"""The lesson builder: a map-reduce LangGraph.

    plan ──Send──> teach(lesson 1) ─┐
         ├─Send──> teach(lesson 2) ─┤
         ├─Send──> teach(lesson n) ─┼──> finish
         └─Send──> glossary ────────┘

``plan`` reads the whole paper and designs a curriculum. Each ``teach`` worker runs in parallel
and writes one lesson (walkthrough, diagram, quiz and exact quotes). Its quotes are checked
against the paper; a lesson that fails the check is rewritten once with the failures pointed out.
"""

from __future__ import annotations

import operator
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .config import Settings
from .grounding import grounding
from .llm import LLM, PaperContext
from .schemas import Glossary, Lesson, LessonPlan, Plan
from .text import normalise

SYSTEM = """You are PaperSensei, a patient tutor who turns research papers into short lessons.
- Teach only what the paper says. Never invent results, numbers or claims. If the paper is unclear, say so.
- Explain like a great teacher: concrete first, then general. Short sentences, plain words, one idea at a time.
- When you quote the paper, copy the words exactly.
- British spelling. Never use em dashes; use a plain hyphen."""

LEVELS: dict[str, str] = {
    "beginner": "a curious newcomer with no background in the field. Define every term, lean on analogies.",
    "practitioner": "a working engineer. Skip the basics, focus on how it works and when to use it.",
    "expert": "a researcher in the field. Be precise and dense, focus on what is new and its limits.",
}


class BuildState(TypedDict, total=False):
    level: str
    plan: dict
    lessons: Annotated[list[dict], operator.add]
    glossary: list[dict]


class TeachTask(TypedDict):
    index: int
    lesson: dict
    level: str


def _emit(event: dict) -> None:
    get_stream_writer()(event)


@dataclass
class Builder:
    llm: LLM
    paper: PaperContext
    settings: Settings

    def build(self):
        graph = StateGraph(BuildState)
        graph.add_node("plan", self.plan)
        graph.add_node("teach", self.teach)
        graph.add_node("glossary", self.glossary)
        graph.add_node("finish", self.finish)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges("plan", self.fan_out, ["teach", "glossary"])
        graph.add_edge("teach", "finish")
        graph.add_edge("glossary", "finish")
        graph.add_edge("finish", END)
        return graph.compile()

    # ── plan ──
    def _outline(self) -> str:
        return "\n".join(f"§ {s.title} (page {s.page})" for s in self.paper.parsed.body)

    async def plan(self, state: BuildState) -> BuildState:
        started = time.perf_counter()
        _emit({"type": "step", "step": "plan", "status": "running"})
        prompt = (
            f"Design a curriculum that teaches this paper to {LEVELS[state['level']]}\n"
            f"Use between 3 and {self.settings.max_lessons} lessons in teaching order. Each lesson must list "
            f"the exact section titles it covers, chosen from this outline:\n{self._outline()}"
        )
        plan = await self.llm.structured(SYSTEM, self.paper, prompt, Plan, self.settings.plan_effort)
        plan.lessons = self._clean(plan.lessons)[: self.settings.max_lessons]
        data = plan.model_dump()
        _emit({"type": "plan", "plan": data, "ms": round((time.perf_counter() - started) * 1000)})
        return {"plan": data}

    def _clean(self, lessons: list[LessonPlan]) -> list[LessonPlan]:
        """Keep only section titles that exist; give orphaned lessons the next unused section."""
        known = {normalise(s.title): s.title for s in self.paper.parsed.body}
        unused = [s.title for s in self.paper.parsed.body]
        for lp in lessons:
            lp.sections = [known[normalise(t)] for t in lp.sections if normalise(t) in known]
            for t in lp.sections:
                if t in unused:
                    unused.remove(t)
        for lp in lessons:
            if not lp.sections and unused:
                lp.sections = [unused.pop(0)]
        return [lp for lp in lessons if lp.sections]

    def fan_out(self, state: BuildState) -> list[Send]:
        tasks = [
            Send("teach", TeachTask(index=i, lesson=lp, level=state["level"]))
            for i, lp in enumerate(state["plan"]["lessons"])
        ]
        return [*tasks, Send("glossary", {"level": state["level"]})]

    # ── teach ──
    async def teach(self, task: TeachTask) -> BuildState:
        lesson = await self.teach_one(task["index"], task["lesson"], task["level"], _emit)
        return {"lessons": [lesson]}

    async def teach_one(self, index: int, plan: dict, level: str, emit: Callable[[dict], None]) -> dict:
        started = time.perf_counter()
        emit({"type": "lesson_started", "index": index, "title": plan["title"]})
        parsed = self.paper.parsed
        sections = [s for s in parsed.sections if s.title in plan["sections"]]
        excerpt = "\n\n".join(f"§ {s.title}\n{parsed.text_of(s)}" for s in sections)
        prompt = (
            f"Lesson: {plan['title']}\nGoal: {plan['goal']}\nAudience: {LEVELS[level]}\n\n"
            f"Teach the sections below, using the full paper for context. For the diagram, pick `flow` for a "
            f"process or architecture and `compare` when the section contrasts two approaches. The quiz should test "
            f"understanding, not recall of a number.\n\nSections to teach:\n{excerpt}"
        )
        attempts, checks, score = 0, [], 0.0
        while True:
            attempts += 1
            lesson = await self.llm.structured(SYSTEM, self.paper, prompt, Lesson, self.settings.lesson_effort)
            score, checks = grounding([q.text for q in lesson.quotes], parsed)
            if score >= self.settings.min_grounding or attempts > 1:
                break
            failed = "\n".join(f"- {c.text}" for c in checks if not c.verified)
            emit({"type": "lesson_retry", "index": index, "grounding": score})
            prompt += (
                f"\n\nPrevious attempt: these quotes do not appear in the paper. Quote only sentences that "
                f"appear word for word, and drop any claim you cannot support:\n{failed}"
            )
        result = {
            "index": index,
            "plan": plan,
            "level": level,
            **lesson.model_dump(),
            "sections": [{"title": s.title, "page": s.page} for s in sections],
            "quote_checks": [c.__dict__ for c in checks],
            "grounding": round(score, 2),
            "attempts": attempts,
            "ms": round((time.perf_counter() - started) * 1000),
        }
        emit({"type": "lesson", "lesson": result})
        return result

    # ── glossary ──
    async def glossary(self, state: dict) -> BuildState:
        prompt = f"List the terms a reader who is {LEVELS[state['level']]} would need defined to follow this paper."
        glossary = await self.llm.structured(SYSTEM, self.paper, prompt, Glossary, self.settings.lesson_effort)
        text = normalise(" ".join(p.text for p in self.paper.parsed.passages))
        # Only keep terms that literally occur, so the UI can highlight them in the lessons.
        terms = [t.model_dump() for t in glossary.terms if normalise(t.term) and normalise(t.term) in text]
        _emit({"type": "glossary", "terms": terms})
        return {"glossary": terms}

    async def finish(self, state: BuildState) -> BuildState:
        lessons = sorted(state.get("lessons", []), key=lambda lesson: lesson["index"])
        overall = sum(lesson["grounding"] for lesson in lessons) / max(len(lessons), 1)
        _emit({"type": "done", "lessons": len(lessons), "grounding": round(overall, 2)})
        return {"lessons": []}
