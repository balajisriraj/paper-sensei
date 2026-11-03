from papersensei.graph import Builder
from papersensei.llm import ScriptedLLM


async def run(builder):
    events = [e async for e in builder.build().astream({"level": "beginner", "lessons": []}, stream_mode="custom")]
    return events


async def test_builds_plan_lessons_and_glossary(paper, settings):
    events = await run(Builder(ScriptedLLM(), paper, settings))
    kinds = [e["type"] for e in events if e["type"] != "step"]
    assert kinds[0] == "plan" and kinds[-1] == "done"
    lessons = [e["lesson"] for e in events if e["type"] == "lesson"]
    plan = next(e["plan"] for e in events if e["type"] == "plan")
    assert sorted(lesson["index"] for lesson in lessons) == list(range(len(plan["lessons"])))
    assert all(lesson["grounding"] == 1.0 and lesson["attempts"] == 1 for lesson in lessons)
    terms = next(e["terms"] for e in events if e["type"] == "glossary")
    assert any(t["term"] == "BM25" for t in terms)


async def test_plan_only_references_real_sections(paper, settings):
    events = await run(Builder(ScriptedLLM(), paper, settings))
    plan = next(e["plan"] for e in events if e["type"] == "plan")
    real = {s.title for s in paper.parsed.body}
    assert all(set(lp["sections"]) <= real and lp["sections"] for lp in plan["lessons"])
    assert len(plan["lessons"]) <= settings.max_lessons


async def test_ungrounded_lesson_is_rewritten_once(paper, settings):
    events = await run(Builder(ScriptedLLM(bad_quotes_first=True), paper, settings))
    retries = [e for e in events if e["type"] == "lesson_retry"]
    lessons = [e["lesson"] for e in events if e["type"] == "lesson"]
    assert len(retries) == len(lessons)
    assert all(lesson["attempts"] == 2 and lesson["grounding"] == 1.0 for lesson in lessons)


def test_clean_maps_fuzzy_titles_and_fills_gaps(paper, settings):
    from papersensei.schemas import LessonPlan

    b = Builder(ScriptedLLM(), paper, settings)
    cleaned = b._clean(
        [
            LessonPlan(title="a", goal="g", sections=["3 method", "Not a section"]),
            LessonPlan(title="b", goal="g", sections=[]),
        ]
    )
    assert cleaned[0].sections == ["3 Method"]
    assert cleaned[1].sections == ["Abstract"]
