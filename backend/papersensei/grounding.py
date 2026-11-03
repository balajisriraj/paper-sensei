"""Checks that every quote a lesson relies on actually appears in the paper.

The model is asked for exact quotes. PDF extraction mangles spacing, hyphens and ligatures, so
matching is done on normalised text, with a longest-common-run fallback for small differences.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .pdf import ParsedPaper
from .text import normalise, tokens

MATCH = 0.85


@dataclass
class QuoteCheck:
    text: str
    verified: bool
    passage: int | None
    page: int | None
    score: float


def check_quote(quote: str, paper: ParsedPaper) -> QuoteCheck:
    q = normalise(quote)
    if len(q) < 12:
        return QuoteCheck(quote, False, None, None, 0.0)
    for p in paper.passages:
        if q in normalise(p.text):
            return QuoteCheck(quote, True, p.id, p.page, 1.0)
    # Fuzzy: compare against the passages that share the most words with the quote.
    words = set(tokens(quote))
    candidates = sorted(paper.passages, key=lambda p: -len(words & set(tokens(p.text))))[:3]
    best, best_score = None, 0.0
    for p in candidates:
        text = normalise(p.text)
        m = SequenceMatcher(None, q, text, autojunk=False).find_longest_match(0, len(q), 0, len(text))
        score = m.size / len(q)
        if score > best_score:
            best, best_score = p, score
    ok = best is not None and best_score >= MATCH
    return QuoteCheck(quote, ok, best.id if ok else None, best.page if ok else None, round(best_score, 2))


def grounding(quotes: list[str], paper: ParsedPaper) -> tuple[float, list[QuoteCheck]]:
    checks = [check_quote(q, paper) for q in quotes]
    if not checks:
        return 0.0, checks
    return sum(c.verified for c in checks) / len(checks), checks
