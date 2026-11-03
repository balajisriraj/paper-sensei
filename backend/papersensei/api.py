"""HTTP API. Build progress and tutor answers stream as Server-Sent Events."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from .config import Settings, get_settings
from .llm import LLMRefusal
from .pdf import PDFError
from .service import Service

log = logging.getLogger("papersensei")
LevelName = Literal["beginner", "practitioner", "expert"]


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=6000)


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=1500)
    history: list[Turn] = Field(default_factory=list, max_length=20)
    level: LevelName = "beginner"


class ArxivBody(BaseModel):
    url: str = Field(max_length=300)
    level: LevelName = "beginner"


class LevelBody(BaseModel):
    level: LevelName = "beginner"


def _sse(events):
    async def gen():
        async for event in events:
            yield {"event": event["type"], "data": json.dumps(event)}

    return EventSourceResponse(gen())


def create_app(settings: Settings | None = None, service: Service | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = service or Service.from_settings(settings)
        yield

    app = FastAPI(title="PaperSensei", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

    def svc(request: Request) -> Service:
        return request.app.state.service

    def paper_or_404(request: Request, paper_id: str) -> dict:
        paper = svc(request).store.get(paper_id)
        if not paper:
            raise HTTPException(404, "No such paper.")
        return paper

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "llm": settings.llm,
            "model": settings.model if settings.llm == "anthropic" else "scripted",
        }

    @app.get("/api/papers")
    async def papers(request: Request) -> list[dict]:
        return svc(request).store.list()

    @app.post("/api/papers", status_code=201)
    async def upload(request: Request, file: UploadFile = File(...), level: LevelName = Form("beginner")) -> dict:
        data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        try:
            return {"id": svc(request).add_pdf(file.filename or "paper.pdf", data, level)}
        except PDFError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/papers/sample", status_code=201)
    async def sample(request: Request, body: LevelBody) -> dict:
        return {"id": svc(request).add_sample(body.level)}

    @app.post("/api/papers/arxiv", status_code=201)
    async def arxiv(request: Request, body: ArxivBody) -> dict:
        try:
            return {"id": await svc(request).add_arxiv(body.url, body.level)}
        except PDFError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/papers/{paper_id}")
    async def paper(paper_id: str, request: Request) -> dict:
        return paper_or_404(request, paper_id)

    @app.delete("/api/papers/{paper_id}")
    async def delete(paper_id: str, request: Request) -> dict:
        return {"deleted": svc(request).store.delete(paper_id)}

    @app.get("/api/papers/{paper_id}/pdf")
    async def pdf(paper_id: str, request: Request) -> FileResponse:
        paper = paper_or_404(request, paper_id)
        return FileResponse(
            svc(request).store.pdf_path(paper_id), media_type="application/pdf", filename=paper["filename"]
        )

    @app.get("/api/papers/{paper_id}/events")
    async def events(paper_id: str, request: Request) -> EventSourceResponse:
        paper_or_404(request, paper_id)
        return _sse(svc(request).events(paper_id))

    @app.post("/api/papers/{paper_id}/lessons/{index}/rewrite")
    async def rewrite(paper_id: str, index: int, body: LevelBody, request: Request) -> dict:
        paper_or_404(request, paper_id)
        try:
            return await svc(request).rewrite(paper_id, index, body.level)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/papers/{paper_id}/ask")
    async def ask(paper_id: str, body: AskBody, request: Request) -> EventSourceResponse:
        paper_or_404(request, paper_id)

        async def stream():
            try:
                async for event in svc(request).ask(
                    paper_id, body.question, [t.model_dump() for t in body.history], body.level
                ):
                    yield event
            except LLMRefusal:
                yield {"type": "error", "message": "I can't help with that one."}
            except Exception:
                log.exception("tutor failed")
                yield {"type": "error", "message": "Something went wrong. Try again?"}

        return _sse(stream())

    return app
