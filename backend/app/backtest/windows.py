"""Generates rolling as-of dates for the backtest, spaced ~quarterly, per
.claude/skills/fintrixa-backtest-methodology."""
from datetime import date

STEP_TRADING_DAYS = 63  # ~1 quarter


def generate_rolling_windows(
    master_calendar: list[date], min_history_days: int, horizon_trading_days: int
) -> list[date]:
    """master_calendar: sorted distinct trade_date values across the whole
    universe. Returns as-of dates spaced STEP_TRADING_DAYS apart, bounded
    so each has at least min_history_days of calendar before it and
    horizon_trading_days after it -- individual stocks are further
    filtered per-window by their own actual history (a stock listed later
    simply won't participate in early windows)."""
    start = min_history_days
    end = len(master_calendar) - horizon_trading_days
    if end <= start:
        return []
    return [master_calendar[i] for i in range(start, end, STEP_TRADING_DAYS)]
