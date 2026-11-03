"""Command line: ``papersensei serve | learn <pdf> | eval``."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .config import get_settings


def _serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("papersensei.api:create_app", factory=True, host=args.host, port=args.port, reload=args.reload)


def _learn(args: argparse.Namespace) -> None:
    from .service import Service

    async def run() -> None:
        service = Service.from_settings(get_settings())
        pdf = Path(args.pdf) if args.pdf else service.settings.sample_pdf
        paper_id = service.add_pdf(pdf.name, pdf.read_bytes(), args.level)
        async for event in service.events(paper_id):
            kind = event["type"]
            if kind == "plan":
                print(f"\n{event['plan']['title']}\n{event['plan']['tldr']}\n")
            elif kind == "lesson":
                lesson = event["lesson"]
                print(f"  ✓ {lesson['index'] + 1}. {lesson['title']}  grounding {lesson['grounding']:.0%}")
            elif kind == "lesson_retry":
                print(f"  ↻ lesson {event['index'] + 1}: quotes didn't check out, rewriting")
            elif kind == "glossary":
                print(f"  ✓ glossary: {len(event['terms'])} terms")
            elif kind == "done":
                print(f"\nReady. Overall grounding {event['grounding']:.0%}. Paper id {paper_id}")
            elif kind == "error":
                print(event["message"], file=sys.stderr)

    asyncio.run(run())


def _eval(args: argparse.Namespace) -> None:
    from .evals import run

    sys.exit(0 if asyncio.run(run(verbose=args.verbose)) else 1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="papersensei", description="Turn research papers into lessons.")
    commands = parser.add_subparsers(required=True)

    serve = commands.add_parser("serve", help="run the HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(run=_serve)

    learn = commands.add_parser("learn", help="build lessons for a PDF in the terminal")
    learn.add_argument("pdf", nargs="?", help="path to a PDF (defaults to the bundled sample)")
    learn.add_argument("--level", default="beginner", choices=["beginner", "practitioner", "expert"])
    learn.set_defaults(run=_learn)

    evals = commands.add_parser("eval", help="run the evaluation suite")
    evals.add_argument("--verbose", action="store_true")
    evals.set_defaults(run=_eval)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
