"""Small text helpers shared by the grounding checks and the scripted model."""

from __future__ import annotations

import re
import unicodedata

STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "has",
        "have",
        "i",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "this",
        "to",
        "was",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
        "do",
        "does",
        "did",
        "how",
        "can",
        "about",
        "they",
        "them",
        "their",
        "there",
        "these",
        "those",
        "than",
        "then",
        "into",
        "also",
        "more",
        "most",
        "such",
        "not",
        "no",
        "paper",
    ]
)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) if len(s.split()) >= 4]


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 2]


def normalise(text: str) -> str:
    """Fold the differences PDF extraction introduces: ligatures, quotes, hyphenation, spacing, case."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"-\s+", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return text.strip()
