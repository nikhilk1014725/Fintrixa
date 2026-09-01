from datetime import date, timedelta

import pandas as pd

from app.backtest.replay import replay_technical_score
from app.scoring.technical import compute_technical_score


def test_replay_technical_score_ignores_data_after_as_of():
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(250)]
    values = [100.0 + (i % 7) for i in range(250)]  # mild variation, avoids degenerate RSI
    values[249] = 100000.0  # far-future spike, must not affect the as-of-day-200 replay
    closes = pd.Series(values, index=pd.Index(dates))
    volumes = pd.Series([1000.0 + (i % 5) for i in range(250)], index=pd.Index(dates))

    as_of = dates[199]

    # Ground truth: compute_technical_score on the series manually truncated
    # to the same cutoff -- if replay_technical_score matches this exactly,
    # it proves the replay never saw anything after `as_of`.
    truncated_closes = closes.iloc[:200]
    truncated_volumes = volumes.iloc[:200]
    expected = compute_technical_score(truncated_closes, truncated_volumes)

    result = replay_technical_score(closes, volumes, as_of)

    assert result == expected


def test_replay_technical_score_insufficient_history_excluded():
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(50)]
    closes = pd.Series([100.0] * 50, index=pd.Index(dates))
    volumes = pd.Series([1000.0] * 50, index=pd.Index(dates))

    result = replay_technical_score(closes, volumes, dates[-1])

    assert result["score"] is None
    assert "insufficient price history" in result["excluded_reason"]
