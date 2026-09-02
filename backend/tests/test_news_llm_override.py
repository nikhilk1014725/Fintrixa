from datetime import datetime

from app.models import NewsCorroboration, Score
from app.news_llm.override import apply_red_flag_override


def _score(long_term_label="Strong Buy", short_term_label="Buy"):
    return Score(
        stock_id=1,
        computed_at=datetime.utcnow(),
        fundamental_score=80.0,
        technical_score=70.0,
        long_term_score=85.0,
        short_term_score=75.0,
        long_term_label=long_term_label,
        short_term_label=short_term_label,
        explanation="test",
        excluded_reason=None,
    )


def _corroboration(red_flags):
    return NewsCorroboration(
        stock_id=1,
        computed_at=datetime.utcnow(),
        bull_case="bull",
        bear_case="bear",
        red_flags=red_flags,
        confidence="Corroborated",
        sources=[],
    )


def test_no_corroboration_no_override():
    result = apply_red_flag_override(_score(), None)

    assert result["long_term_label"] == "Strong Buy"
    assert result["short_term_label"] == "Buy"
    assert result["override_reason"] is None


def test_empty_red_flags_no_override():
    result = apply_red_flag_override(_score(), _corroboration([]))

    assert result["long_term_label"] == "Strong Buy"
    assert result["override_reason"] is None


def test_active_red_flag_caps_strong_buy_and_buy_to_hold():
    result = apply_red_flag_override(
        _score(long_term_label="Strong Buy", short_term_label="Buy"),
        _corroboration(["pending litigation"]),
    )

    assert result["long_term_label"] == "Hold"
    assert result["short_term_label"] == "Hold"
    assert result["override_reason"] is not None
    assert "pending litigation" in result["override_reason"]


def test_active_red_flag_does_not_raise_hold_or_avoid():
    result = apply_red_flag_override(
        _score(long_term_label="Hold", short_term_label="Avoid"),
        _corroboration(["regulatory action"]),
    )

    assert result["long_term_label"] == "Hold"
    assert result["short_term_label"] == "Avoid"


def test_no_score_no_override():
    result = apply_red_flag_override(None, _corroboration(["litigation"]))

    assert result["long_term_label"] is None
    assert result["short_term_label"] is None
