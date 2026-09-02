import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

MIN_HISTORY_DAYS = 200
VOLUME_MA_WINDOW = 20
MOMENTUM_WINDOW = 5


def compute_technical_score(closes: pd.Series, volumes: pd.Series) -> dict:
    """RSI, 50/200 DMA, Volume, and MACD components of the Technical
    Trigger, per .claude/skills/fintrixa-scoring-formula. All four
    components are now implemented (100 of 100 spec points) -- see
    docs/superpowers/specs/2026-09-02-complete-technical-trigger-design.md
    for the bucket-boundary rationale on the two newly-added components."""
    if len(closes) < MIN_HISTORY_DAYS:
        return {
            "score": None,
            "excluded_reason": (
                f"insufficient price history: {len(closes)} days, "
                f"need >= {MIN_HISTORY_DAYS} for 200-day moving average"
            ),
        }

    if len(volumes) < VOLUME_MA_WINDOW or volumes.iloc[-VOLUME_MA_WINDOW:].isna().any():
        return {
            "score": None,
            "excluded_reason": (
                f"insufficient or missing volume data: need >= {VOLUME_MA_WINDOW} "
                f"clean days for the volume moving average"
            ),
        }

    rsi = RSIIndicator(close=closes, window=14).rsi().iloc[-1]
    sma50 = SMAIndicator(close=closes, window=50).sma_indicator().iloc[-1]
    sma200 = SMAIndicator(close=closes, window=200).sma_indicator().iloc[-1]
    last_close = closes.iloc[-1]

    # RSI component (0-25 pts): 30-45 or 50-65 scores highest
    if 30 <= rsi <= 45 or 50 <= rsi <= 65:
        rsi_pts = 25.0
    elif 20 <= rsi < 30 or 65 < rsi <= 70:
        rsi_pts = 15.0
    else:
        rsi_pts = 5.0

    # Moving average component (0-30 pts)
    above_both = last_close > sma50 and last_close > sma200
    golden_cross = sma50 > sma200
    if above_both and golden_cross:
        ma_pts = 30.0
    elif above_both:
        ma_pts = 20.0
    elif not golden_cross and last_close < sma50 and last_close < sma200:
        ma_pts = 0.0
    else:
        ma_pts = 10.0

    # Volume component (0-20 pts): above-average volume confirming price
    # direction scores higher than a move on thin volume. Confirmed
    # selling pressure (downtrend + above-average volume) scores lowest --
    # this is a Buy-oriented formula, so confirmed weakness is worse than
    # an unconfirmed drift.
    uptrend = last_close > closes.iloc[-1 - MOMENTUM_WINDOW]
    volume_ma = volumes.rolling(VOLUME_MA_WINDOW).mean().iloc[-1]
    above_avg_volume = volumes.iloc[-1] > volume_ma
    if uptrend and above_avg_volume:
        volume_pts = 20.0
    elif not uptrend and above_avg_volume:
        volume_pts = 0.0
    else:
        volume_pts = 10.0

    # MACD component (0-25 pts): bullish crossover with rising histogram
    # scores highest.
    macd_indicator = MACD(close=closes)
    macd_line = macd_indicator.macd().iloc[-1]
    signal_line = macd_indicator.macd_signal().iloc[-1]
    histogram = macd_indicator.macd_diff()
    bullish = macd_line > signal_line
    rising_histogram = histogram.iloc[-1] > histogram.iloc[-2]
    if bullish and rising_histogram:
        macd_pts = 25.0
    elif bullish:
        macd_pts = 15.0
    elif rising_histogram:
        macd_pts = 10.0
    else:
        macd_pts = 0.0

    # All four components are now implemented -- raw is already 0-100,
    # no scaling needed (the old /55.0*100 scaling is removed).
    score = round(rsi_pts + ma_pts + volume_pts + macd_pts, 1)

    return {"score": score, "excluded_reason": None}
