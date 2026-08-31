from app.scoring.verdict import combine_scores


def test_strong_buy_long_term_weights_fundamentals_more():
    result = combine_scores(fundamental_score=90.0, technical_score=40.0)
    # 0.7*90 + 0.3*40 = 75 -> Buy
    assert result["long_term_label"] == "Buy"
    assert result["long_term_score"] == 75.0


def test_strong_buy_short_term_weights_technical_more():
    result = combine_scores(fundamental_score=40.0, technical_score=90.0)
    # 0.3*40 + 0.7*90 = 75 -> Buy
    assert result["short_term_label"] == "Buy"
    assert result["short_term_score"] == 75.0


def test_missing_either_score_excludes_both_verdicts():
    result = combine_scores(fundamental_score=None, technical_score=90.0)
    assert result["long_term_score"] is None
    assert result["long_term_label"] is None
    assert result["short_term_score"] is None
    assert "fundamental" in result["excluded_reason"]


def test_label_thresholds():
    assert combine_scores(85.0, 85.0)["long_term_label"] == "Strong Buy"
    assert combine_scores(65.0, 65.0)["long_term_label"] == "Buy"
    assert combine_scores(45.0, 45.0)["long_term_label"] == "Hold"
    assert combine_scores(20.0, 20.0)["long_term_label"] == "Avoid"
