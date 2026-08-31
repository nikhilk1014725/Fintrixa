import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

MIN_HISTORY_DAYS = 200


def compute_technical_score(closes: pd.Series, volumes: pd.Series) -> dict:
    """RSI + 50/200 DMA components of the Technical Trigger, per
    .claude/skills/fintrixa-scoring-formula. Volume and MACD components
    are added in the scoring-breadth plan; this covers the two components
    that most directly need price history depth, to prove the exclusion
    rule works before adding the rest."""
    if len(closes) < MIN_HISTORY_DAYS:
        return {
            "score": None,
            "excluded_reason": (
                f"insufficient price history: {len(closes)} days, "
                f"need >= {MIN_HISTORY_DAYS} for 200-day moving average"
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

    # Scaled to 0-100 using only the two implemented components (55 pts max)
    # until volume/MACD land in the breadth plan.
    raw = rsi_pts + ma_pts
    score = round((raw / 55.0) * 100, 1)

    return {"score": score, "excluded_reason": None}
