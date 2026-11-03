"""Model layer.

Two kinds of call:
- ``structured``: Claude reads the original PDF (text and figures) and answers in a JSON schema.
  The PDF block is cached, so the planner pays for it once and every lesson after reads it from cache.
- ``tutor``: the parsed passages go in as one custom-content document with citations on. Claude
  cites the exact block it used, and each block index maps back to a section and a page.

``ScriptedLLM`` answers the same calls deterministically from the parsed text, so the pipeline,
the grounding checks and the API can be tested offline.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from .config import Settings
from .pdf import ParsedPaper
from .text import sentences, tokens

T = TypeVar("T", bound=BaseModel)
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMRefusal(RuntimeError):
    pass


@dataclass
class PaperContext:
    pdf: bytes
    parsed: ParsedPaper


class LLM(Protocol):
    async def structured(self, system: str, paper: PaperContext, prompt: str, schema: type[T], effort: str) -> T: ...

    def tutor(self, system: str, paper: PaperContext, messages: list[dict], effort: str) -> AsyncIterator[dict]: ...


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema for structured outputs: every property required, no extra keys."""

    def tighten(node: Any) -> Any:
        if isinstance(node, dict):
            node = {k: tighten(v) for k, v in node.items() if k not in ("title", "default")}
            if node.get("type") == "object" and "properties" in node:
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
        elif isinstance(node, list):
            node = [tighten(v) for v in node]
        return node

    schema = model.model_json_schema()
    defs = schema.pop("$defs", None)
    schema = tighten(schema)
    if defs:
        schema["$defs"] = {k: tighten(v) for k, v in defs.items()}
    return schema


class AnthropicLLM:
    def __init__(self, settings: Settings) -> None:
        import anthropic

        self.client = anthropic.AsyncAnthropic()
        self.model = settings.model

    @staticmethod
    def _pdf_block(paper: PaperContext) -> dict:
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(paper.pdf).decode()},
            "title": paper.parsed.title,
            "cache_control": {"type": "ephemeral"},
        }

    @staticmethod
    def _passages_block(paper: PaperContext) -> dict:
        return {
            "type": "document",
            "source": {"type": "content", "content": [{"type": "text", "text": p.text} for p in paper.parsed.passages]},
            "title": paper.parsed.title,
            "context": "Each content block is one passage of the paper, in reading order.",
            "citations": {"enabled": True},
            "cache_control": {"type": "ephemeral"},
        }

    async def structured(self, system: str, paper: PaperContext, prompt: str, schema: type[T], effort: str) -> T:
        response = await self.client.beta.messages.create(
            model=self.model,
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": [self._pdf_block(paper), {"type": "text", "text": prompt}]}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": strict_schema(schema)}},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise LLMRefusal("Claude declined this request.")
        text = next(block.text for block in response.content if block.type == "text")
        return schema.model_validate(json.loads(text))

    async def tutor(self, system: str, paper: PaperContext, messages: list[dict], effort: str) -> AsyncIterator[dict]:
        # The document rides on the first user turn so the cached prefix (system + paper) never changes.
        first, *rest = messages
        convo = [{"role": "user", "content": [self._passages_block(paper), {"type": "text", "text": first["content"]}]}]
        convo += [{"role": m["role"], "content": m["content"]} for m in rest]
        async with self.client.beta.messages.stream(
            model=self.model,
            max_tokens=2000,
            system=system,
            messages=convo,
            output_config={"effort": effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            async for event in stream:
                if event.type != "content_block_delta":
                    continue
                if event.delta.type == "text_delta":
                    yield {"type": "text", "text": event.delta.text}
                elif event.delta.type == "citations_delta":
                    c = event.delta.citation
                    if c.type == "content_block_location":
                        yield {"type": "citation", "block": c.start_block_index, "cited_text": c.cited_text}
            final = await stream.get_final_message()
        if final.stop_reason == "refusal":
            raise LLMRefusal("Claude declined to answer.")


class ScriptedLLM:
    """Deterministic stand-in: builds plans, lessons and cited answers from the parsed text."""

    def __init__(self, delay: float = 0.0, bad_quotes_first: bool = False) -> None:
        self.delay = delay
        # Test hook: the first draft of every lesson invents a quote, so the grounding loop has to fix it.
        self.bad_quotes_first = bad_quotes_first

    async def _pause(self, factor: float = 1.0) -> None:
        if self.delay:
            await asyncio.sleep(self.delay * factor)

    async def structured(self, system: str, paper: PaperContext, prompt: str, schema: type[T], effort: str) -> T:
        await self._pause(25)
        build = {"Plan": self._plan, "Glossary": self._glossary, "Lesson": self._lesson}[schema.__name__]
        return schema.model_validate(build(paper.parsed, prompt))

    # ── planning ──
    def _plan(self, paper: ParsedPaper, prompt: str) -> dict:
        body = paper.body
        abstract = next((s for s in body if s.title.lower() == "abstract"), body[0])
        teach = [s for s in body if s is not abstract] or body
        lessons = [
            {
                "title": re.sub(r"^[\dIVX.]+\s+", "", s.title),
                "goal": f"Explain {re.sub(r'^[0-9IVX.]+[ ]+', '', s.title).lower()} in your own words.",
                "sections": [s.title],
            }
            for s in teach[:6]
        ]
        abstract_sentences = sentences(paper.text_of(abstract))
        return {
            "title": paper.title,
            "tldr": " ".join(abstract_sentences[:2]),
            "why_it_matters": abstract_sentences[-1] if abstract_sentences else paper.title,
            "prerequisites": ["Search and ranking basics", "What an embedding is"],
            "lessons": lessons,
        }

    def _glossary(self, paper: ParsedPaper, prompt: str) -> dict:
        terms, seen = [], set()
        for section in paper.body:
            for sentence in sentences(paper.text_of(section)):
                for match in re.finditer(
                    r"\b([A-Z]{2,}\d*|[A-Z][a-z]+ (?:[a-z]+ ){0,2}(?:fusion|search|retrieval))\b", sentence
                ):
                    term = match.group(1)
                    if term.lower() in seen or len(terms) >= 8:
                        continue
                    seen.add(term.lower())
                    terms.append({"term": term, "definition": sentence, "section": section.title})
        return {"terms": terms}

    def _lesson(self, paper: ParsedPaper, prompt: str) -> dict:
        wanted = re.findall(r"^§ (.+)$", prompt, re.M)
        sections = [s for s in paper.sections if s.title in wanted] or paper.body[:1]
        text = "\n\n".join(paper.text_of(s) for s in sections)
        said = sentences(text)
        title = re.search(r"^Lesson: (.+)$", prompt, re.M)
        revising = "Previous attempt" in prompt
        quotes = (
            ["The authors prove the method is optimal for every corpus."]
            if self.bad_quotes_first and not revising
            else said[:3]
        )
        walk = said[:6]
        concept = [w for w in tokens(text) if len(w) > 5][:6] or ["idea", "method", "result"]
        return {
            "title": title.group(1) if title else sections[0].title,
            "walkthrough": "\n\n".join([" ".join(walk[:3]), " ".join(walk[3:6])]).strip(),
            "key_points": said[:3],
            "analogy": "Think of it like asking two librarians and trusting the books both of them recommend.",
            "diagram": {
                "title": f"How {concept[0]} fits together",
                "kind": "flow",
                "nodes": [
                    {"id": f"n{i}", "label": w.title(), "detail": "from the paper"} for i, w in enumerate(concept[:4])
                ],
                "edges": [
                    {"source": f"n{i}", "target": f"n{i + 1}", "label": ""} for i in range(min(3, len(concept) - 1))
                ],
                "left_title": "",
                "right_title": "",
                "rows": [],
            },
            "quiz": {
                "question": f"Which statement matches the paper's section on {sections[0].title}?",
                "options": [
                    said[0] if said else text[:80],
                    "The paper does not discuss this.",
                    "The opposite is true.",
                    "Only for images.",
                ],
                "answer": 0,
                "explanation": "This is stated directly in the paper.",
            },
            "quotes": [{"text": q, "supports": "walkthrough"} for q in quotes],
        }

    # ── tutoring ──
    async def tutor(self, system: str, paper: PaperContext, messages: list[dict], effort: str) -> AsyncIterator[dict]:
        question = set(tokens(messages[-1]["content"]))
        passages = paper.parsed.passages
        bags = [set(tokens(p.text)) for p in passages]
        # Rare words matter more: weight overlap by inverse document frequency.
        idf = {w: math.log(len(bags) / (1 + sum(w in b for b in bags))) + 1 for w in question}
        scored = sorted(
            ((sum(idf[w] for w in question & bag), p) for bag, p in zip(bags, passages, strict=True)),
            key=lambda x: (-x[0], x[1].id),
        )
        hits = [p for score, p in scored[:2] if score >= 3.5]
        await self._pause(10)
        if not hits:
            for word in [
                "The",
                "paper",
                "doesn't",
                "cover",
                "that,",
                "as",
                "far",
                "as",
                "I",
                "can",
                "see.",
                "Try",
                "asking",
                "about",
                "its",
                "method",
                "or",
                "results.",
            ]:
                await self._pause()
                yield {"type": "text", "text": word + " "}
            return
        yield {"type": "text", "text": "Here's what the paper says. "}
        for p in hits:
            best = max(sentences(p.text), key=lambda s: len(question & set(tokens(s))))
            for word in best.split(" "):
                await self._pause()
                yield {"type": "text", "text": word + " "}
            yield {"type": "citation", "block": p.id, "cited_text": best}


def make_llm(settings: Settings) -> LLM:
    if settings.llm == "scripted":
        return ScriptedLLM(delay=settings.scripted_delay)
    if settings.llm == "anthropic":
        return AnthropicLLM(settings)
    raise ValueError(f"Unknown LLM backend: {settings.llm}")
