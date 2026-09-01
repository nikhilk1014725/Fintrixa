# Sub-project B — Broader Universe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded 17-ticker seed list with a live-fetched NIFTY 100 universe from NSE's public CSV, using NSE's own sector classification for sector_pe peer-grouping, per `docs/superpowers/specs/2026-09-01-broader-universe-design.md`.

**Architecture:** Backend-only, `backend/app/ingestion/` — new pure-parsing + thin-network module (`nse_universe.py`), an additive optional param on `fetch_fundamentals`, and `scripts/seed_universe.py` rewired to use both. No scoring-formula change — backtest gate does not apply.

**Tech Stack:** Python 3.11, `requests` (already a transitive dependency via yfinance, confirmed present in the venv), pytest, `unittest.mock`.

---

### Task 1: NIFTY 100 constituent fetch + parse

**Files:**
- Create: `backend/app/ingestion/nse_universe.py`
- Test: `backend/tests/test_nse_universe.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_nse_universe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion.nse_universe'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_nse_universe.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Verify the real endpoint live (not just the mocked test)**

Run: `curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" -o /tmp/nifty100.csv -w "%{http_code}\n" https://archives.nseindia.com/content/indices/ind_nifty100list.csv && head -5 /tmp/nifty100.csv && wc -l /tmp/nifty100.csv`
Expected: `200`, header row matches `Company Name,Industry,Symbol,Series,ISIN Code`, 101 lines total (1 header + 100 constituents). If the User-Agent above gets blocked or the format differs from what's assumed, adjust `REQUEST_HEADERS`/`parse_nifty100_csv` accordingly and re-run Steps 2-4 before proceeding — do not skip this live check, the mocked tests alone don't prove the real endpoint still works.

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/nse_universe.py backend/tests/test_nse_universe.py
git commit -m "feat: fetch live NIFTY 100 constituents from NSE"
```

---

### Task 2: sector_hint on fetch_fundamentals

**Files:**
- Modify: `backend/app/ingestion/yfinance_client.py`
- Modify: `backend/tests/test_yfinance_client.py`

**Context:** `fetch_fundamentals` currently always uses yfinance's `info.get("sector")` (a US-style GICS string, often missing/inaccurate for NSE tickers). NSE's own Industry classification (from Task 1's `fetch_nifty100_constituents`) is more accurate for Indian peer-comparison. This task adds an optional override, backward compatible with existing callers.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_yfinance_client.py` (add `from unittest.mock import Mock, patch` to imports, and `from app.ingestion.yfinance_client import fetch_fundamentals` alongside the existing imports from that module):

```python
@patch("app.ingestion.yfinance_client.yf.Ticker")
def test_fetch_fundamentals_uses_sector_hint_when_provided(mock_ticker_cls):
    mock_ticker = Mock()
    mock_ticker.info = {
        "sector": "Energy",
        "trailingPE": 20.0,
        "returnOnEquity": 0.15,
        "debtToEquity": 0.3,
    }
    mock_ticker_cls.return_value = mock_ticker

    result = fetch_fundamentals("RELIANCE.NS", sector_hint="Oil Gas & Consumable Fuels")

    assert result["sector"] == "Oil Gas & Consumable Fuels"


@patch("app.ingestion.yfinance_client.yf.Ticker")
def test_fetch_fundamentals_falls_back_to_yfinance_sector_without_hint(mock_ticker_cls):
    mock_ticker = Mock()
    mock_ticker.info = {
        "sector": "Energy",
        "trailingPE": 20.0,
        "returnOnEquity": 0.15,
        "debtToEquity": 0.3,
    }
    mock_ticker_cls.return_value = mock_ticker

    result = fetch_fundamentals("RELIANCE.NS")

    assert result["sector"] == "Energy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_yfinance_client.py -v -k sector_hint`
Expected: FAIL — `TypeError: fetch_fundamentals() got an unexpected keyword argument 'sector_hint'`

- [ ] **Step 3: Write minimal implementation**

In `backend/app/ingestion/yfinance_client.py`, replace the `fetch_fundamentals` function:

```python
def fetch_fundamentals(ticker: str, sector_hint: str | None = None) -> dict:
    """Best-effort fundamentals from yfinance .info — incomplete for many
    NSE tickers. screener.in fallback is added in the ingestion-breadth
    plan; this returns whatever yfinance has, with explicit None for the
    rest so callers never mistake missing for zero.

    `sector_hint`, when provided (e.g. NSE's own Industry classification
    from `nse_universe.fetch_nifty100_constituents`), is used instead of
    yfinance's `sector` field -- more accurate for Indian peer-comparison
    than yfinance's US-style GICS string. Falls back to yfinance's sector
    when not provided."""
    info = yf.Ticker(ticker).info
    return {
        "sector": sector_hint if sector_hint is not None else info.get("sector"),
        "trailing_pe": info.get("trailingPE"),
        "sector_pe": None,  # filled in by enrich_sector_pe() across the fetched universe
        "return_on_equity": info.get("returnOnEquity"),
        "return_on_capital_employed": None,  # not exposed by yfinance
        "debt_to_equity": info.get("debtToEquity"),
        "revenue_cagr_3y": None,  # requires multi-year financials; breadth plan
        "profit_cagr_3y": None,
        "promoter_holding_trend": None,  # not available from yfinance
        "pledged_shares_pct": None,
        "auditor_changed_recently": None,
        "negative_equity": None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_yfinance_client.py -v`
Expected: PASS (all tests in this file, including the two new ones)

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/yfinance_client.py backend/tests/test_yfinance_client.py
git commit -m "feat: allow sector_hint override on fetch_fundamentals"
```

---

### Task 3: wire seed_universe.py to the live NIFTY 100 universe

**Files:**
- Modify: `backend/scripts/seed_universe.py`

**Context:** No unit tests for this script (it never had any — it's a manual/scheduled integration script, verified by actually running it, same as before). Tasks 1-2 provide everything this task wires together.

- [ ] **Step 1: Replace the full contents of `backend/scripts/seed_universe.py`**

```python
"""Fetch the live NIFTY 100 universe, score it, persist it.

Supersedes the old hardcoded 17-ticker starter list: pulls the current
NIFTY 100 constituents from NSE (see app.ingestion.nse_universe), uses
NSE's own Industry classification for sector_pe peer-grouping (see
app.ingestion.enrichment.enrich_sector_pe) instead of yfinance's sector
field.
"""
import time
from datetime import datetime

import pandas as pd

from app.db import SessionLocal
from app.ingestion.enrichment import enrich_sector_pe
from app.ingestion.nse_universe import fetch_nifty100_constituents
from app.ingestion.yfinance_client import (
    fetch_fundamentals,
    fetch_price_history,
    normalize_price_history,
    persist_price_history,
)
from app.models import Score, Stock
from app.scoring.fundamental import compute_fundamental_score
from app.scoring.technical import compute_technical_score
from app.scoring.verdict import combine_scores

RATE_LIMIT_DELAY_SECONDS = 0.5


def main():
    db = SessionLocal()

    constituents = fetch_nifty100_constituents()
    print(f"fetched {len(constituents)} NIFTY 100 constituents from NSE")

    # Fetch fundamentals for the whole batch first so enrich_sector_pe has
    # the full universe to group/average over before any scoring happens.
    fundamentals_by_ticker = {}
    for c in constituents:
        fundamentals_by_ticker[c["ticker"]] = fetch_fundamentals(
            c["ticker"], sector_hint=c["sector"]
        )
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

    fundamentals_by_ticker = enrich_sector_pe(fundamentals_by_ticker)

    for c in constituents:
        ticker = c["ticker"]
        stock = db.query(Stock).filter_by(ticker=ticker).one_or_none()
        if stock is None:
            stock = Stock(ticker=ticker, name=c["name"])
            db.add(stock)
            db.flush()
        elif stock.name != c["name"]:
            stock.name = c["name"]

        history = fetch_price_history(ticker)
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

        rows = normalize_price_history(history)
        persist_price_history(db, stock.id, rows)

        closes = pd.Series(history["Close"].values) if not history.empty else pd.Series(dtype=float)
        volumes = pd.Series(history["Volume"].values) if not history.empty else pd.Series(dtype=float)

        technical = compute_technical_score(closes, volumes)
        fundamentals = fundamentals_by_ticker[ticker]
        fundamental = compute_fundamental_score(fundamentals)
        combined = combine_scores(fundamental["score"], technical["score"])

        excluded_reason = (
            fundamental["excluded_reason"] or technical["excluded_reason"] or combined["excluded_reason"]
        )

        db.add(
            Score(
                stock_id=stock.id,
                computed_at=datetime.utcnow(),
                fundamental_score=fundamental["score"],
                technical_score=technical["score"],
                long_term_score=combined["long_term_score"],
                short_term_score=combined["short_term_score"],
                long_term_label=combined["long_term_label"],
                short_term_label=combined["short_term_label"],
                explanation=combined["explanation"],
                excluded_reason=excluded_reason,
            )
        )
        db.commit()

        if excluded_reason:
            print(f"scored {ticker}: excluded_reason={excluded_reason}")
        else:
            print(
                f"scored {ticker}: long_term={combined['long_term_label']}, "
                f"short_term={combined['short_term_label']}"
            )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests pass (this script has no direct tests, but this confirms nothing else broke)

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/seed_universe.py
git commit -m "feat: seed the live NIFTY 100 universe instead of a hardcoded 17-ticker list"
```

---

### Task 4: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests pass, including the new `test_nse_universe.py` and the two new `fetch_fundamentals` tests.

- [ ] **Step 2: Actually run the seed script against the local Postgres**

Run: `cd backend && .venv/bin/python scripts/seed_universe.py`
Expected: prints "fetched 100 NIFTY 100 constituents from NSE" (real live NSE call, not mocked), then one line per ticker (`scored {ticker}: ...` or `scored {ticker}: excluded_reason=...`). Confirm the run completes without an unhandled exception. Note how long it took (a few minutes is expected and fine).

- [ ] **Step 3: Confirm the database reflects the broader universe**

Run: `cd backend && .venv/bin/python -c "from app.db import SessionLocal; from app.models import Stock, Score; db = SessionLocal(); print('stocks:', db.query(Stock).count()); print('scores:', db.query(Score).count())"`
Expected: `stocks:` close to 100 (may be slightly under 100 if a ticker had no yfinance data at all and hit an unhandled edge case — investigate if so, don't just accept a much lower number silently). `scores:` should be >= `stocks:` count (one Score row per ticker from this run, plus any carried over from the old 17-ticker runs).

- [ ] **Step 4: Confirm sector_pe coverage improved**

Run: `cd backend && .venv/bin/python -c "
from app.db import SessionLocal
from app.models import Score
db = SessionLocal()
total = db.query(Score).count()
excluded_sector_pe = db.query(Score).filter(Score.excluded_reason.like('%sector_pe%')).count()
print(f'{excluded_sector_pe} of {total} scores excluded for missing sector_pe')
"`
Expected: a meaningfully smaller fraction excluded for `sector_pe` specifically than before this change (previously several of the 17 tickers were excluded because their sector only had 1 usable peer in the small batch — with ~100 tickers spread across NSE's real Industry categories, most sectors should now have 2+ members). Report the actual before/after numbers, don't just assert improvement without evidence.

- [ ] **Step 5: Restart the backend dev server and spot-check the live frontend**

If the backend dev server (`uvicorn app.api.main:app --port 8000`) is running from before this change, it doesn't need restarting for this (it queries the DB fresh per-request, no in-memory caching of the stock list). Load `http://localhost:5173` in a browser (or via the same Playwright approach used in Phase A's verification) and confirm: Home's subtext now reads "Screened from our tracked universe of ~100 Indian stocks" (the real new count), Discover shows the larger list. Screenshot as evidence.

- [ ] **Step 6: If anything in Steps 1-5 surfaces a real defect, fix it and re-verify**

Fix inline, re-run the relevant step, then commit:

```bash
git add -A
git commit -m "fix: <describe what verification caught>"
```

If nothing needed fixing, no commit is required for this task.
