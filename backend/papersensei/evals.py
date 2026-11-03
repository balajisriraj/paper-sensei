"""Evaluation suite: lesson quality checks plus tutor grounding over the bundled sample paper."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .config import ROOT, get_settings
from .service import Service

CASES = ROOT / "evals" / "tutor.yaml"
DASHES = re.compile("[\\u2013\\u2014]")  # the house style uses plain hyphens


def lesson_issues(lesson: dict, min_grounding: float) -> list[str]:
    """Structural checks every lesson must pass, whatever model wrote it."""
    issues = []
    if lesson["grounding"] < min_grounding:
        issues.append(f"grounding {lesson['grounding']:.0%}")
    quiz = lesson["quiz"]
    if len(quiz["options"]) != 4 or not 0 <= quiz["answer"] < 4:
        issues.append("quiz needs four options and a valid answer")
    d = lesson["diagram"]
    if d["kind"] == "flow":
        ids = {n["id"] for n in d["nodes"]}
        if len(ids) < 2 or any(e["source"] not in ids or e["target"] not in ids for e in d["edges"]):
            issues.append("flow diagram has dangling edges")
    elif not d["rows"]:
        issues.append("compare diagram has no rows")
    if DASHES.search(lesson["walkthrough"]):
        issues.append("em or en dash in walkthrough")
    return issues


async def run(verbose: bool = False) -> bool:
    settings = get_settings()
    service = Service.from_settings(settings)
    paper_id = service.add_sample("beginner")
    async for _ in service.events(paper_id):
        pass
    paper = service.store.get(paper_id)
    ok = True

    print(f"Lessons for: {paper['title']}")
    for lesson in paper["lessons"]:
        issues = lesson_issues(lesson, settings.min_grounding)
        ok &= not issues
        if verbose or issues:
            print(
                f"  {'PASS' if not issues else 'FAIL'}  lesson {lesson['index'] + 1}: {lesson['title']}  {', '.join(issues)}"
            )
    print(
        f"  lessons       {sum(not lesson_issues(x, settings.min_grounding) for x in paper['lessons'])}/{len(paper['lessons'])}"
    )

    cases = yaml.safe_load(Path(CASES).read_text(encoding="utf-8"))
    passed = cited_ok = cited_all = 0
    for case in cases:
        events = [e async for e in service.ask(paper_id, case["question"], [], "beginner")]
        cites = [e for e in events if e["type"] == "citation"]
        cited_all += len(cites)
        cited_ok += sum(c["verified"] for c in cites)
        if case.get("uncited"):
            good = not cites
        else:
            good = any(c["section"] == case["section"] for c in cites) and all(c["verified"] for c in cites)
        passed += good
        if verbose or not good:
            print(f"  {'PASS' if good else 'FAIL'}  tutor {case['id']}: cited {[c['section'] for c in cites]}")
    print(f"  tutor         {passed}/{len(cases)}")
    print(f"  citations     {cited_ok}/{cited_all} verified against the paper")
    service.store.delete(paper_id)
    return ok and passed == len(cases) and cited_ok == cited_all
