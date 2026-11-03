"""PDF to a structured paper: pages, sections and numbered passages.

Passages are the unit of citation. Each becomes one block of the document Claude reads, so a
citation's block index maps straight back to a section and a page.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from io import BytesIO

from pypdf import PdfReader

KNOWN = (
    "abstract|introduction|background|related work|method|methods|methodology|approach|experiments?|"
    "evaluation|results|discussion|limitations|conclusions?|future work|acknowledge?ments|references|appendix"
)
NUMBERED = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[IVX]+\.|[A-Z]\.)\s+[A-Z][^.!?]{1,80}$")
NAMED = re.compile(rf"^(?:{KNOWN})(?:\s+[A-Za-z ]{{0,40}})?$", re.I)
END_MATTER = re.compile(r"^(?:\d+\.?\s+)?(?:references|bibliography|acknowledge?ments)\b", re.I)


@dataclass
class Passage:
    id: int
    section: str
    page: int
    text: str


@dataclass
class Section:
    title: str
    page: int
    passages: list[int] = field(default_factory=list)
    end_matter: bool = False


@dataclass
class ParsedPaper:
    title: str
    pages: int
    sections: list[Section]
    passages: list[Passage]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ParsedPaper:
        return cls(
            title=d["title"],
            pages=d["pages"],
            sections=[Section(**s) for s in d["sections"]],
            passages=[Passage(**p) for p in d["passages"]],
        )

    def text_of(self, section: Section) -> str:
        return "\n\n".join(self.passages[i].text for i in section.passages)

    @property
    def body(self) -> list[Section]:
        return [s for s in self.sections if not s.end_matter]


class PDFError(ValueError):
    pass


def _is_heading(line: str) -> bool:
    words = line.split()
    if not 1 <= len(words) <= 12 or line.endswith((".", ",", ";", ":")):
        return False
    return bool(NUMBERED.match(line) or NAMED.match(line))


def _paragraphs(lines: list[str]) -> list[str]:
    """Rejoin wrapped lines. A short line that ends a sentence closes its paragraph."""
    width = max((len(line) for line in lines), default=0)
    out: list[str] = []
    buf = ""
    for line in lines:
        hyphenated = buf.endswith("-") and line[:1].islower()
        buf = buf[:-1] + line if hyphenated else f"{buf} {line}".strip()
        if line.endswith((".", "?", "!", ".)")) and len(line) < width * 0.8:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def _windows(paragraph: str, target: int = 500) -> list[str]:
    """Split long paragraphs on sentence boundaries so each citation points at a few sentences."""
    if len(paragraph) <= target * 1.3:
        return [paragraph]
    out, buf = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", paragraph):
        if buf and len(buf) + len(sentence) > target:
            out.append(buf)
            buf = sentence
        else:
            buf = f"{buf} {sentence}".strip()
    if buf:
        out.append(buf)
    return out


def parse_pdf(data: bytes, max_pages: int = 40) -> ParsedPaper:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:  # pypdf raises many types for malformed files
        raise PDFError("That file doesn't look like a readable PDF.") from exc
    if reader.is_encrypted:
        raise PDFError("The PDF is password protected.")
    if len(reader.pages) > max_pages:
        raise PDFError(f"PaperSensei handles papers up to {max_pages} pages.")

    pages = [(page.extract_text() or "") for page in reader.pages]
    if sum(len(p.strip()) for p in pages) < 200:
        raise PDFError("No text found. Scanned PDFs need OCR first.")

    meta_title = (reader.metadata.title if reader.metadata else None) or ""
    first_lines = [line.strip() for line in pages[0].splitlines() if line.strip()]

    sections: list[Section] = [Section(title="Front matter", page=1)]
    pending: list[str] = []
    pending_page = 1
    passages: list[Passage] = []

    def flush() -> None:
        nonlocal pending
        for para in _paragraphs(pending):
            if len(para) < 25 and passages:
                passages[-1].text += " " + para
                continue
            for piece in _windows(para):
                passages.append(Passage(len(passages), sections[-1].title, pending_page, piece))
                sections[-1].passages.append(passages[-1].id)
        pending = []

    for number, text in enumerate(pages, 1):
        for line in (raw_line.strip() for raw_line in text.splitlines()):
            if not line or re.fullmatch(r"\d{1,3}", line):  # blank lines and page numbers
                continue
            if _is_heading(line):
                flush()
                sections.append(Section(title=line, page=number, end_matter=bool(END_MATTER.match(line))))
                pending_page = number
                continue
            if not pending:
                pending_page = number
            pending.append(line)
    flush()

    sections = [s for s in sections if s.passages]
    title = meta_title.strip() or (" ".join(first_lines[:2]) if first_lines else "Untitled paper")
    if sections and sections[0].title == "Front matter" and len(sections) > 1:
        # The title block itself isn't teaching material.
        sections[0].end_matter = True
    return ParsedPaper(title=title, pages=len(pages), sections=sections, passages=passages)
