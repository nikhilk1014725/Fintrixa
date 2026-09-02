import pandas as pd

from app.scoring.technical import compute_technical_score


def _uptrend_prices(n=260, start=100.0, step=0.3):
    return pd.Series([start + step * i for i in range(n)])


def _staircase(n, daily_delta, start=100.0):
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] + daily_delta)
    return pd.Series(prices)


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


def test_confirming_volume_scores_higher_than_thin_volume_in_identical_uptrend():
    # Same price series both times (isolates the volume component's
    # contribution -- RSI/MA/MACD are identical between the two calls
    # since they only depend on `closes`).
    closes = _staircase(220, daily_delta=0.3)

    thin_volume = pd.Series([1_000_000] * 215 + [500_000] * 5)  # recent volume below its own 20-day average
    confirming_volume = pd.Series([1_000_000] * 215 + [3_000_000] * 5)  # recent volume spikes above average

    thin_result = compute_technical_score(closes, thin_volume)
    confirming_result = compute_technical_score(closes, confirming_volume)

    assert thin_result["score"] is not None
    assert confirming_result["score"] is not None
    assert confirming_result["score"] > thin_result["score"]


def test_confirmed_downtrend_scores_lower_than_thin_volume_downtrend():
    closes = _staircase(220, daily_delta=-0.3)

    thin_volume = pd.Series([1_000_000] * 215 + [500_000] * 5)
    confirming_volume = pd.Series([1_000_000] * 215 + [3_000_000] * 5)

    thin_result = compute_technical_score(closes, thin_volume)
    confirming_result = compute_technical_score(closes, confirming_volume)

    assert thin_result["score"] is not None
    assert confirming_result["score"] is not None
    # confirmed selling pressure (high volume on a downtrend) must score
    # LOWER than an unconfirmed thin-volume drift down -- this is the
    # inverse of the uptrend case above.
    assert confirming_result["score"] < thin_result["score"]


def test_accelerating_uptrend_scores_higher_than_decelerating_uptrend():
    # Both end in positive territory, both above their moving averages --
    # isolates the MACD histogram-direction contribution. Accelerating:
    # slow-then-fast. Decelerating: fast-then-slow (momentum fading even
    # though still technically an uptrend).
    accelerating = pd.concat(
        [_staircase(200, daily_delta=0.1), _staircase(20, daily_delta=1.0, start=120.0)],
        ignore_index=True,
    )
    decelerating = pd.concat(
        [_staircase(200, daily_delta=1.0), _staircase(20, daily_delta=0.1, start=300.0)],
        ignore_index=True,
    )
    volumes = pd.Series([1_000_000] * 220)

    accelerating_result = compute_technical_score(accelerating, volumes)
    decelerating_result = compute_technical_score(decelerating, volumes)

    assert accelerating_result["score"] is not None
    assert decelerating_result["score"] is not None
    assert accelerating_result["score"] > decelerating_result["score"]


def test_insufficient_volume_history_excluded_not_zero():
    closes = _staircase(220, daily_delta=0.3)
    volumes = pd.Series([1_000_000] * 15)  # shorter than VOLUME_MA_WINDOW=20

    result = compute_technical_score(closes, volumes)

    assert result["score"] is None
    assert "volume" in result["excluded_reason"].lower()


def test_nan_in_recent_volume_excluded_not_silently_scored():
    import math

    closes = _staircase(220, daily_delta=0.3)
    volume_values = [1_000_000] * 220
    volume_values[-3] = math.nan  # NaN within the trailing 20-day window used for the volume MA
    volumes = pd.Series(volume_values)

    result = compute_technical_score(closes, volumes)

    assert result["score"] is None
    assert "volume" in result["excluded_reason"].lower()
