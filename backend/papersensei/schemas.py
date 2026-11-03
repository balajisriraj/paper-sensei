"""Structured outputs. Each model is also the JSON schema Claude must answer in."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["beginner", "practitioner", "expert"]


class LessonPlan(BaseModel):
    title: str = Field(description="Short, plain-language lesson title.")
    goal: str = Field(description="One sentence: what the learner can explain after this lesson.")
    sections: list[str] = Field(description="Exact titles of the paper sections this lesson covers.")


class Plan(BaseModel):
    title: str = Field(description="The paper's title.")
    tldr: str = Field(description="Two plain sentences: what the paper did and what it found.")
    why_it_matters: str = Field(description="One or two sentences on why a practitioner should care.")
    prerequisites: list[str] = Field(description="Two to four concepts a reader should know first.")
    lessons: list[LessonPlan] = Field(description="Three to six lessons in teaching order.")


class Term(BaseModel):
    term: str = Field(description="The term exactly as the paper writes it.")
    definition: str = Field(description="A one-sentence plain-language definition.")
    section: str = Field(description="Title of the section where it is introduced.")


class Glossary(BaseModel):
    terms: list[Term] = Field(description="Six to twelve terms a newcomer would trip on.")


class Node(BaseModel):
    id: str
    label: str = Field(description="Two to four words.")
    detail: str = Field(description="A short phrase, under eight words.")


class Edge(BaseModel):
    source: str
    target: str
    label: str = Field(description="Optional short verb; empty string for none.")


class Row(BaseModel):
    label: str
    left: str
    right: str


class Diagram(BaseModel):
    title: str
    kind: Literal["flow", "compare"] = Field(
        description="flow: a process or architecture as nodes and edges. compare: two things side by side."
    )
    nodes: list[Node] = Field(description="For flow: three to seven nodes. Empty for compare.")
    edges: list[Edge] = Field(description="For flow: edges between node ids. Empty for compare.")
    left_title: str = Field(description="For compare: the left column heading. Empty for flow.")
    right_title: str = Field(description="For compare: the right column heading. Empty for flow.")
    rows: list[Row] = Field(description="For compare: three to six rows. Empty for flow.")


class Quiz(BaseModel):
    question: str
    options: list[str] = Field(description="Exactly four options.")
    answer: int = Field(description="Index of the correct option, 0 to 3.")
    explanation: str = Field(description="Why the answer is right, in one or two sentences.")


class Quote(BaseModel):
    text: str = Field(description="A sentence copied exactly, word for word, from the paper.")
    supports: str = Field(description="Which claim in the walkthrough this quote backs up.")


class Lesson(BaseModel):
    title: str
    walkthrough: str = Field(
        description="150 to 300 words of plain-language explanation in markdown paragraphs. No headings."
    )
    key_points: list[str] = Field(description="Three takeaways, one sentence each.")
    analogy: str = Field(description="One everyday analogy that makes the core idea click.")
    diagram: Diagram
    quiz: Quiz
    quotes: list[Quote] = Field(description="Two to four exact quotes from the paper backing the walkthrough.")
