"""Computes forward returns in trading-day horizons (not calendar days --
per-ticker trading-day counts are the standard backtest convention and
match compute_technical_score's own MIN_HISTORY_DAYS=200 trading-day
threshold), per .claude/skills/fintrixa-backtest-methodology."""
from datetime import date

import pandas as pd


def compute_forward_return(
    closes: pd.Series, as_of: date, horizon_trading_days: int
) -> float | None:
    """closes indexed by trade_date (ascending). Returns None if `as_of`
    isn't in the index or there isn't enough data after it to reach the
    horizon -- never guesses a partial-period return."""
    if as_of not in closes.index:
        return None
    as_of_pos = closes.index.get_loc(as_of)
    forward_pos = as_of_pos + horizon_trading_days
    if forward_pos >= len(closes):
        return None
    start_price = closes.iloc[as_of_pos]
    end_price = closes.iloc[forward_pos]
    if start_price == 0:
        return None
    return (end_price - start_price) / start_price
