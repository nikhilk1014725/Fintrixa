"""Live NIFTY 100 index-constituent fetch from NSE's public archive.

NSE publishes a free, no-auth CSV of NIFTY 100 constituents at a stable
URL. Verified live: `archives.nseindia.com` (not `www.nseindia.com`, which
404s for this path) returns HTTP 200 with a plain browser User-Agent
header, no cookies/session needed. Columns are
`Company Name,Industry,Symbol,Series,ISIN Code`.

No caching here -- the CSV is ~100 rows and NIFTY 100 rebalances only
twice a year, so re-fetching it on every ingestion run is cheap and always
current.
"""
import csv
import io

import requests

NIFTY100_CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_nifty100_csv(csv_text: str) -> list[dict]:
    """Parse the NSE NIFTY 100 constituents CSV into ticker/name/sector rows.

    `Symbol` gets a `.NS` suffix to match this project's existing yfinance
    ticker convention (e.g. `BAJAJ-AUTO.NS` -- hyphenated symbols pass
    through unchanged). `Company Name` -> `name`, `Industry` -> `sector`.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    return [
        {
            "ticker": f"{row['Symbol'].strip()}.NS",
            "name": row["Company Name"].strip(),
            "sector": row["Industry"].strip(),
        }
        for row in reader
    ]


def fetch_nifty100_constituents() -> list[dict]:
    """Fetch and parse the live NIFTY 100 constituent list from NSE.

    Raises on a non-200 response or network failure -- an ingestion run
    that can't get the universe should fail loudly, not silently seed an
    empty one.
    """
    response = requests.get(NIFTY100_CSV_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    return parse_nifty100_csv(response.text)
