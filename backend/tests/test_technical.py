import pandas as pd

from app.scoring.technical import compute_technical_score


def _uptrend_prices(n=260, start=100.0, step=0.3):
    return pd.Series([start + step * i for i in range(n)])


def test_strong_uptrend_scores_high():
    closes = _uptrend_prices()
    volumes = pd.Series([1_000_000] * len(closes))

    result = compute_technical_score(closes, volumes)

    assert result["score"] >= 60
    assert result["excluded_reason"] is None


def test_insufficient_history_is_excluded_not_zero():
    closes = pd.Series([100.0, 101.0, 102.0])  # far short of 200-day window
    volumes = pd.Series([1_000_000, 1_000_000, 1_000_000])

    result = compute_technical_score(closes, volumes)

    assert result["score"] is None
    assert "insufficient" in result["excluded_reason"].lower()
