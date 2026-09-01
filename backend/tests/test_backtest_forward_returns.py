from datetime import date
import math

import pandas as pd
import pytest

from app.backtest.forward_returns import compute_forward_return


def _series(dates, values):
    return pd.Series(values, index=pd.Index(dates))


def test_compute_forward_return_known_prices():
    dates = [date(2024, 1, i) for i in range(1, 11)]
    closes = _series(dates, [100, 101, 102, 103, 104, 105, 106, 107, 108, 110])

    result = compute_forward_return(closes, as_of=date(2024, 1, 1), horizon_trading_days=9)

    assert result == pytest.approx((110 - 100) / 100)


def test_compute_forward_return_none_when_as_of_missing():
    dates = [date(2024, 1, i) for i in range(1, 11)]
    closes = _series(dates, list(range(100, 110)))

    result = compute_forward_return(closes, as_of=date(2024, 1, 15), horizon_trading_days=1)

    assert result is None


def test_compute_forward_return_none_when_insufficient_forward_room():
    dates = [date(2024, 1, i) for i in range(1, 11)]
    closes = _series(dates, list(range(100, 110)))

    result = compute_forward_return(closes, as_of=date(2024, 1, 9), horizon_trading_days=5)

    assert result is None


def test_compute_forward_return_none_when_start_price_is_nan():
    dates = [date(2024, 1, i) for i in range(1, 11)]
    values = [100, 101, 102, 103, 104, 105, 106, 107, 108, 110]
    values[0] = math.nan
    closes = _series(dates, values)

    result = compute_forward_return(closes, as_of=date(2024, 1, 1), horizon_trading_days=9)

    assert result is None


def test_compute_forward_return_none_when_end_price_is_nan():
    dates = [date(2024, 1, i) for i in range(1, 11)]
    values = [100, 101, 102, 103, 104, 105, 106, 107, 108, 110]
    values[9] = math.nan
    closes = _series(dates, values)

    result = compute_forward_return(closes, as_of=date(2024, 1, 1), horizon_trading_days=9)

    assert result is None


def test_compute_forward_return_none_when_start_price_negative():
    dates = [date(2024, 1, i) for i in range(1, 11)]
    values = [100, 101, 102, 103, 104, 105, 106, 107, 108, 110]
    values[0] = -5.0
    closes = _series(dates, values)

    result = compute_forward_return(closes, as_of=date(2024, 1, 1), horizon_trading_days=9)

    assert result is None
