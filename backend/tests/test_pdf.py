import pytest

from papersensei.pdf import PDFError, _windows, parse_pdf


def test_sample_is_split_into_sections_and_passages(paper):
    parsed = paper.parsed
    titles = [s.title for s in parsed.sections]
    assert titles[:3] == ["Front matter", "Abstract", "1 Introduction"]
    assert "References" in titles
    assert [s.title for s in parsed.sections if s.end_matter] == ["Front matter", "References"]
    assert all(p.id == i for i, p in enumerate(parsed.passages))
    assert parsed.passages[-1].page == 2


def test_body_excludes_front_and_end_matter(paper):
    assert all(not s.end_matter for s in paper.parsed.body)
    assert paper.parsed.body[0].title == "Abstract"


def test_long_paragraphs_split_on_sentences():
    para = " ".join(f"Sentence number {i} is here and it carries some words." for i in range(30))
    pieces = _windows(para)
    assert len(pieces) > 1
    assert " ".join(pieces) == para
    assert all(p.endswith(".") for p in pieces)


def test_round_trip(paper):
    from papersensei.pdf import ParsedPaper

    assert ParsedPaper.from_dict(paper.parsed.to_dict()) == paper.parsed


def test_rejects_non_pdf():
    with pytest.raises(PDFError):
        parse_pdf(b"not a pdf at all")
