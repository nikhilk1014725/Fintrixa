import pandas as pd

from app.ingestion.yfinance_client import normalize_price_history


def test_normalize_price_history_maps_expected_columns():
    raw = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [104.0],
            "Volume": [123456.0],
        },
        index=pd.to_datetime(["2026-08-28"]),
    )

    rows = normalize_price_history(raw)

    assert rows == [
        {
            "trade_date": "2026-08-28",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 123456.0,
        }
    ]


def test_normalize_price_history_empty_input_returns_empty_list():
    assert normalize_price_history(pd.DataFrame()) == []
