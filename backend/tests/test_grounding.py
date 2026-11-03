from papersensei.grounding import check_quote, grounding


def test_exact_quote_is_verified_with_page(paper):
    c = check_quote("Retrieval is the quiet half of a grounded assistant.", paper.parsed)
    assert c.verified and c.page == 1 and c.score == 1.0


def test_extraction_noise_is_tolerated(paper):
    # Different case, curly quotes, stray hyphenation and spacing.
    c = check_quote("RANKS are   always compa- rable.", paper.parsed)
    assert c.verified


def test_invented_quote_fails(paper):
    c = check_quote("The authors prove the method is optimal for every corpus.", paper.parsed)
    assert not c.verified and c.passage is None


def test_score_is_share_verified(paper):
    score, checks = grounding(
        ["Ranks are always comparable.", "Fusion beats every reranker ever built by a mile."], paper.parsed
    )
    assert score == 0.5 and [c.verified for c in checks] == [True, False]
