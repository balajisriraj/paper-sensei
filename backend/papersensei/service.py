"""Application service: ingest papers, build lessons in the background, tutor with citations."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from .config import Settings
from .graph import LEVELS, Builder
from .llm import LLM, LLMRefusal, PaperContext, make_llm
from .pdf import ParsedPaper, PDFError, parse_pdf
from .store import Store
from .text import normalise

log = logging.getLogger("papersensei")

TUTOR = """You are PaperSensei, tutoring someone through the paper in the attached document.
- Answer only from the paper and cite the passages you rely on. If the paper doesn't cover the question,
  say so in one sentence and suggest a related question it does answer.
- Keep answers under 150 words unless asked for more. Plain words, short paragraphs.
- The learner is {level}
- British spelling. Never use em dashes; use a plain hyphen."""

ARXIV = re.compile(r"^/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?/?$")


class Bus:
    """Replayable event stream for one build: late subscribers get history, then live events."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.closed = False
        self._changed = asyncio.Condition()

    async def publish(self, event: dict, final: bool = False) -> None:
        async with self._changed:
            self.events.append(event)
            self.closed = self.closed or final
            self._changed.notify_all()

    async def subscribe(self) -> AsyncIterator[dict]:
        seen = 0
        while True:
            async with self._changed:
                await self._changed.wait_for(lambda seen=seen: len(self.events) > seen or self.closed)
                fresh, seen = self.events[seen:], len(self.events)
                closed = self.closed
            for event in fresh:
                yield event
            if closed and seen == len(self.events):
                return


@dataclass
class Service:
    settings: Settings
    llm: LLM
    store: Store
    buses: dict[str, Bus] = field(default_factory=dict)
    _tasks: set[asyncio.Task] = field(default_factory=set)

    @classmethod
    def from_settings(cls, settings: Settings, llm: LLM | None = None) -> Service:
        return cls(settings, llm or make_llm(settings), Store(settings.data_dir))

    # ── ingest ──
    def add_pdf(self, filename: str, data: bytes, level: str = "beginner") -> str:
        if level not in LEVELS:
            raise ValueError("Unknown level.")
        if len(data) > self.settings.max_upload_mb * 1024 * 1024:
            raise PDFError(f"PDFs up to {self.settings.max_upload_mb} MB, please.")
        if not data.startswith(b"%PDF"):
            raise PDFError("That file isn't a PDF.")
        parsed = parse_pdf(data, self.settings.max_pages)
        paper_id = self.store.create(filename, data, parsed.to_dict(), level)
        self.start_build(paper_id)
        return paper_id

    def add_sample(self, level: str = "beginner") -> str:
        return self.add_pdf(self.settings.sample_pdf.name, self.settings.sample_pdf.read_bytes(), level)

    async def add_arxiv(self, url: str, level: str = "beginner") -> str:
        parsed = urlparse(url.strip())
        match = ARXIV.match(parsed.path)
        if parsed.scheme not in ("http", "https") or parsed.hostname not in ("arxiv.org", "www.arxiv.org") or not match:
            raise PDFError("Paste an arXiv link like https://arxiv.org/abs/1706.03762.")
        pdf_url = f"https://arxiv.org/pdf/{match.group(1)}"
        limit = self.settings.max_upload_mb * 1024 * 1024
        async with (
            httpx.AsyncClient(timeout=30) as client,
            client.stream("GET", pdf_url, follow_redirects=False) as res,
        ):
            if res.status_code != 200:
                raise PDFError(f"arXiv returned {res.status_code} for that paper.")
            chunks, size = [], 0
            async for chunk in res.aiter_bytes():
                size += len(chunk)
                if size > limit:
                    raise PDFError(f"PDFs up to {self.settings.max_upload_mb} MB, please.")
                chunks.append(chunk)
        return self.add_pdf(f"arxiv-{match.group(1)}.pdf", b"".join(chunks), level)

    def context(self, paper_id: str) -> PaperContext:
        paper = self.store.get(paper_id)
        if not paper:
            raise KeyError(paper_id)
        return PaperContext(self.store.pdf_path(paper_id).read_bytes(), ParsedPaper.from_dict(paper["parsed"]))

    # ── build ──
    def start_build(self, paper_id: str) -> None:
        self.buses[paper_id] = Bus()
        task = asyncio.get_running_loop().create_task(self.build(paper_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def build(self, paper_id: str) -> None:
        bus = self.buses.setdefault(paper_id, Bus())
        paper = self.store.get(paper_id)
        try:
            builder = Builder(self.llm, self.context(paper_id), self.settings).build()
            async for event in builder.astream({"level": paper["level"], "lessons": []}, stream_mode="custom"):
                if event["type"] == "plan":
                    self.store.update(paper_id, plan=event["plan"], title=event["plan"]["title"])
                elif event["type"] == "lesson":
                    self.store.save_lesson(paper_id, event["lesson"])
                elif event["type"] == "glossary":
                    self.store.update(paper_id, glossary=event["terms"])
                elif event["type"] == "done":
                    self.store.update(paper_id, status="ready", grounding=event["grounding"])
                    await bus.publish(event, final=True)
                    continue
                await bus.publish(event)
        except Exception as exc:
            log.exception("build failed for %s", paper_id)
            message = (
                "Claude declined to process this paper."
                if isinstance(exc, LLMRefusal)
                else "Building the lessons failed."
            )
            self.store.update(paper_id, status="failed", error=message)
            await bus.publish({"type": "error", "message": message}, final=True)

    async def events(self, paper_id: str) -> AsyncIterator[dict]:
        bus = self.buses.get(paper_id)
        if bus is None:  # built before this process started
            paper = self.store.get(paper_id)
            yield {"type": "done", "lessons": len(paper["lessons"]), "grounding": paper["grounding"]}
            return
        async for event in bus.subscribe():
            yield event

    async def rewrite(self, paper_id: str, index: int, level: str) -> dict:
        paper = self.store.get(paper_id)
        if level not in LEVELS or not paper or not paper["plan"] or not 0 <= index < len(paper["plan"]["lessons"]):
            raise ValueError("No such lesson.")
        builder = Builder(self.llm, self.context(paper_id), self.settings)
        lesson = await builder.teach_one(index, paper["plan"]["lessons"][index], level, lambda e: None)
        self.store.save_lesson(paper_id, lesson)
        return lesson

    # ── tutor ──
    async def ask(self, paper_id: str, question: str, history: list[dict], level: str) -> AsyncIterator[dict]:
        ctx = self.context(paper_id)
        passages = ctx.parsed.passages
        messages = [*history[-8:], {"role": "user", "content": question}]
        cited, verified = 0, 0
        async for event in self.llm.tutor(TUTOR.format(level=LEVELS[level]), ctx, messages, self.settings.tutor_effort):
            if event["type"] == "citation":
                block = event["block"]
                if not 0 <= block < len(passages):
                    continue
                p = passages[block]
                ok = normalise(event["cited_text"]) in normalise(p.text)
                cited, verified = cited + 1, verified + ok
                yield {
                    "type": "citation",
                    "passage": p.id,
                    "page": p.page,
                    "section": p.section,
                    "cited_text": event["cited_text"],
                    "verified": ok,
                }
            else:
                yield event
        yield {"type": "done", "citations": cited, "verified": verified}
