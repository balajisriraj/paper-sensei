"""Builds samples/hybrid-retrieval.pdf: a short, original demo paper used by the tests and the "try a sample" button.

It is written for this project and says so on the first page. Its experiment is illustrative, not a real result.
Run: uv run python scripts/make_sample.py
"""

from pathlib import Path

from fpdf import FPDF

TITLE = "Fusing Rankings: A Practical Look at Hybrid Retrieval for Grounded Assistants"
AUTHORS = "Balaji Sri Raj"
NOTE = "Demo document written for PaperSensei. The experiment is illustrative and not a published result."

SECTIONS = [
    (
        "Abstract",
        [
            "Assistants that answer from documents fail in two familiar ways: they miss the passage that holds the "
            "answer, or they find it and then say something the passage does not support. This paper looks at the "
            "first failure. We compare keyword search, vector search and a simple fusion of the two called "
            "reciprocal rank fusion. On a small illustrative benchmark, fusion finds the right passage more often "
            "than either method alone, needs no training and adds almost no latency. We explain why it works, when "
            "it does not, and how to tell the difference in production.",
        ],
    ),
    (
        "1 Introduction",
        [
            "Retrieval is the quiet half of a grounded assistant. A language model can only cite what it is shown, "
            "so if the right passage never reaches the prompt, no amount of careful prompting will produce a "
            "faithful answer.",
            "Two families of retrieval dominate practice. Keyword search scores a passage by how many of the query's "
            "words it contains, weighted by how rare those words are. Vector search embeds the query and every "
            "passage as points in a shared space and returns the nearest neighbours. Each is strong where the "
            "other is weak, which suggests combining them.",
            "Our contribution is practical rather than novel: a clear account of reciprocal rank fusion, a small "
            "experiment that shows its effect, and a checklist for deciding whether hybrid retrieval is worth it "
            "for a given corpus.",
        ],
    ),
    (
        "2 Background",
        [
            "BM25 is the standard keyword scoring function. It rewards a passage for containing query terms, "
            "rewards rare terms more than common ones through inverse document frequency, and saturates so that "
            "repeating a word many times stops helping. It is exact: a query for an error code finds that code.",
            "Dense retrieval uses a neural encoder to map text to vectors so that passages with similar meaning sit "
            "close together, even when they share no words. A question about cancelling a subscription can match a "
            "passage about ending a plan. Its weakness is the opposite of BM25: rare identifiers, names and numbers "
            "are often blurred together.",
        ],
    ),
    (
        "3 Method",
        [
            "Reciprocal rank fusion merges ranked lists without looking at their scores. Each passage receives, from "
            "every list it appears in, a contribution of one divided by the sum of a constant k and its rank in that "
            "list. The contributions are added and the passages are sorted by the total.",
            "Ignoring raw scores is the point. BM25 scores and cosine similarities live on different scales, and "
            "normalising them is fragile. Ranks are always comparable. The constant k, usually 60, flattens the "
            "advantage of the very top positions, so a passage ranked well by both methods beats one ranked first "
            "by only one of them.",
            "In our setup each method returns its top 20 passages, fusion keeps the best 6, and those 6 are given to "
            "the model as numbered sources it must cite.",
        ],
    ),
    (
        "4 Experiments",
        [
            "We built an illustrative benchmark of 120 questions over a corpus of 900 passages drawn from product "
            "documentation, release notes and support articles. Each question has one passage marked as the answer. "
            "We report recall at 6: the share of questions whose answer passage is among the 6 passages given to "
            "the model.",
            "We compare three systems: BM25 alone, a small open embedding model alone, and reciprocal rank fusion of "
            "the two with k set to 60. All three run on a laptop CPU.",
        ],
    ),
    (
        "5 Results",
        [
            "On this benchmark BM25 alone reached a recall at 6 of 0.71 and vector search alone reached 0.78. Fusion "
            "reached 0.89. Fusion added under 5 milliseconds per query, almost all of it the second search.",
            "The gains were not uniform. Questions containing exact identifiers such as version numbers were "
            "answered best by BM25, and vector search often missed them. Paraphrased questions were answered best "
            "by vector search. Fusion recovered most of both groups, which is why its total is higher than either.",
        ],
    ),
    (
        "6 Limitations",
        [
            "The benchmark is small and illustrative, so the numbers show the shape of the effect rather than its "
            "size. Fusion also cannot rescue a passage that neither method retrieves; if both lists miss it, the "
            "answer is still lost. Finally, fusion treats both methods as equally trustworthy. When one is much "
            "weaker on a corpus, weighting the lists or dropping the weak method can do better.",
        ],
    ),
    (
        "7 Conclusion",
        [
            "Hybrid retrieval with reciprocal rank fusion is cheap, robust and easy to reason about. For assistants "
            "that must cite their sources, it is a sensible default: measure recall on your own questions, keep "
            "both rankings visible for debugging, and only reach for learned rerankers once fusion has stopped "
            "improving.",
        ],
    ),
    (
        "References",
        [
            "Cormack, G. V., Clarke, C. L. A. and Buettcher, S. (2009). Reciprocal rank fusion outperforms Condorcet "
            "and individual rank learning methods. SIGIR.",
            "Robertson, S. and Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. "
            "Foundations and Trends in Information Retrieval.",
        ],
    ),
]


def build(out: Path) -> None:
    pdf = FPDF(format="A4")
    pdf.set_margins(22, 22, 22)
    pdf.set_auto_page_break(True, margin=22)
    pdf.set_title(TITLE)
    pdf.set_author(AUTHORS)
    pdf.add_page()
    pdf.set_font("Times", "B", 17)
    pdf.multi_cell(0, 8, TITLE, align="C")
    pdf.ln(2)
    pdf.set_font("Times", "", 11)
    pdf.cell(0, 6, AUTHORS, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "I", 9)
    pdf.cell(0, 6, NOTE, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for heading, paragraphs in SECTIONS:
        pdf.set_font("Times", "B", 13)
        pdf.ln(2)
        pdf.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Times", "", 11)
        for p in paragraphs:
            pdf.multi_cell(0, 5.6, p, align="J")
            pdf.ln(2)
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "samples" / "hybrid-retrieval.pdf"
    build(target)
    print(f"Wrote {target}")
