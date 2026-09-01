from datetime import date, timedelta

from app.backtest.windows import generate_rolling_windows


def _calendar(n):
    return [date(2020, 1, 1) + timedelta(days=i) for i in range(n)]


def test_generate_rolling_windows_spaced_quarterly():
    calendar = _calendar(500)

    windows = generate_rolling_windows(calendar, min_history_days=200, horizon_trading_days=63)

    assert windows[0] == calendar[200]
    assert windows[1] == calendar[200 + 63]
    assert all(w in calendar for w in windows)


def test_generate_rolling_windows_bounded_by_horizon():
    calendar = _calendar(500)

    windows = generate_rolling_windows(calendar, min_history_days=200, horizon_trading_days=63)

    last_index = calendar.index(windows[-1])
    assert last_index <= len(calendar) - 63


def test_generate_rolling_windows_empty_when_insufficient_calendar():
    calendar = _calendar(100)  # shorter than min_history_days

    windows = generate_rolling_windows(calendar, min_history_days=200, horizon_trading_days=63)

    assert windows == []
