from unittest.mock import Mock, patch

import pytest
import requests

from app.ingestion.nse_universe import fetch_nifty100_constituents, parse_nifty100_csv

SAMPLE_CSV = (
    "Company Name,Industry,Symbol,Series,ISIN Code\n"
    "Reliance Industries Limited,Oil Gas & Consumable Fuels,RELIANCE,EQ,INE002A01018\n"
    "Bajaj Auto Limited,Automobile and Auto Components,BAJAJ-AUTO,EQ,INE917I01010\n"
    "Tata Consultancy Services Limited,Information Technology,TCS,EQ,INE467B01029\n"
)


def test_parse_nifty100_csv_maps_columns_and_appends_ns_suffix():
    rows = parse_nifty100_csv(SAMPLE_CSV)

    assert rows == [
        {
            "ticker": "RELIANCE.NS",
            "name": "Reliance Industries Limited",
            "sector": "Oil Gas & Consumable Fuels",
        },
        {
            "ticker": "BAJAJ-AUTO.NS",
            "name": "Bajaj Auto Limited",
            "sector": "Automobile and Auto Components",
        },
        {
            "ticker": "TCS.NS",
            "name": "Tata Consultancy Services Limited",
            "sector": "Information Technology",
        },
    ]


def test_parse_nifty100_csv_hyphenated_symbol_passes_through():
    rows = parse_nifty100_csv(SAMPLE_CSV)
    bajaj = next(r for r in rows if r["name"] == "Bajaj Auto Limited")
    assert bajaj["ticker"] == "BAJAJ-AUTO.NS"


@patch("app.ingestion.nse_universe.requests.get")
def test_fetch_nifty100_constituents_parses_successful_response(mock_get):
    mock_response = Mock()
    mock_response.text = SAMPLE_CSV
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = fetch_nifty100_constituents()

    assert len(result) == 3
    assert result[0]["ticker"] == "RELIANCE.NS"
    mock_get.assert_called_once()


@patch("app.ingestion.nse_universe.requests.get")
def test_fetch_nifty100_constituents_raises_on_http_error(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status = Mock(side_effect=requests.HTTPError("503 Server Error"))
    mock_get.return_value = mock_response

    with pytest.raises(requests.HTTPError):
        fetch_nifty100_constituents()
