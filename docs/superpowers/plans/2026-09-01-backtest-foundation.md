# Backtest Foundation Implementation Plan (Sub-project C, Stage 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working technical/short-term backtest harness per `docs/superpowers/specs/2026-09-01-backtest-foundation-design.md` and `.claude/skills/fintrixa-backtest-methodology`, and produce a real pass/fail report against the currently-seeded universe.

**Architecture:** New `backend/app/backtest/` module (four small pure/near-pure files + an orchestrator), a one-time price-history backfill script, and a CLI script that runs the release-gate check and prints the report. No scoring-formula change — this stage measures the existing formula.

**Tech Stack:** Python 3.11, pandas, pytest, existing `backend/app/scoring/technical.py` and `backend/app/ingestion/yfinance_client.py` (both reused unmodified).

---

### Task 1: forward returns + rolling windows

**Files:**
- Create: `backend/app/backtest/__init__.py` (empty)
- Create: `backend/app/backtest/forward_returns.py`
- Create: `backend/app/backtest/windows.py`
- Test: `backend/tests/test_backtest_forward_returns.py`
- Test: `backend/tests/test_backtest_windows.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_backtest_forward_returns.py`:
```python
from datetime import date

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
```

`backend/tests/test_backtest_windows.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_forward_returns.py tests/test_backtest_windows.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.backtest'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/backtest/__init__.py`: empty file.

`backend/app/backtest/forward_returns.py`:
```python
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
```

`backend/app/backtest/windows.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_forward_returns.py tests/test_backtest_windows.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/backtest/__init__.py backend/app/backtest/forward_returns.py backend/app/backtest/windows.py backend/tests/test_backtest_forward_returns.py backend/tests/test_backtest_windows.py
git commit -m "feat: add backtest forward-return and rolling-window primitives"
```

---

### Task 2: no-look-ahead technical score replay

**Files:**
- Create: `backend/app/backtest/replay.py`
- Test: `backend/tests/test_backtest_replay.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date, timedelta

import pandas as pd

from app.backtest.replay import replay_technical_score
from app.scoring.technical import compute_technical_score


def test_replay_technical_score_ignores_data_after_as_of():
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(250)]
    values = [100.0 + (i % 7) for i in range(250)]  # mild variation, avoids degenerate RSI
    values[249] = 100000.0  # far-future spike, must not affect the as-of-day-200 replay
    closes = pd.Series(values, index=pd.Index(dates))
    volumes = pd.Series([1000.0 + (i % 5) for i in range(250)], index=pd.Index(dates))

    as_of = dates[199]

    # Ground truth: compute_technical_score on the series manually truncated
    # to the same cutoff -- if replay_technical_score matches this exactly,
    # it proves the replay never saw anything after `as_of`.
    truncated_closes = closes.iloc[:200]
    truncated_volumes = volumes.iloc[:200]
    expected = compute_technical_score(truncated_closes, truncated_volumes)

    result = replay_technical_score(closes, volumes, as_of)

    assert result == expected


def test_replay_technical_score_insufficient_history_excluded():
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(50)]
    closes = pd.Series([100.0] * 50, index=pd.Index(dates))
    volumes = pd.Series([1000.0] * 50, index=pd.Index(dates))

    result = replay_technical_score(closes, volumes, dates[-1])

    assert result["score"] is None
    assert "insufficient price history" in result["excluded_reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_replay.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.backtest.replay'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/backtest/replay.py`:
```python
"""Replays the technical score formula as of a historical date, using only
data that existed at that date (no look-ahead) -- per
.claude/skills/fintrixa-backtest-methodology."""
from datetime import date

import pandas as pd

from app.scoring.technical import compute_technical_score


def replay_technical_score(closes: pd.Series, volumes: pd.Series, as_of: date) -> dict:
    """closes/volumes must be pd.Series indexed by trade_date (ascending).
    Slices to data on or before `as_of` and calls the existing
    compute_technical_score unmodified -- this is what guarantees no
    look-ahead: the score literally cannot see data after `as_of`."""
    sliced_closes = closes[closes.index <= as_of]
    sliced_volumes = volumes[volumes.index <= as_of]
    return compute_technical_score(sliced_closes, sliced_volumes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_replay.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/backtest/replay.py backend/tests/test_backtest_replay.py
git commit -m "feat: add no-look-ahead technical score replay"
```

---

### Task 3: quartile hit-rate evaluation

**Files:**
- Create: `backend/app/backtest/hitrate.py`
- Test: `backend/tests/test_backtest_hitrate.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.backtest.hitrate import evaluate_window


def test_evaluate_window_discriminating_data_passes_both_conditions():
    # Scores perfectly correlated with returns -- top quartile (highest
    # scores) should clearly beat the median, bottom quartile clearly below.
    scored_returns = [(float(i), float(i) / 1000) for i in range(0, 100, 5)]  # 20 points

    result = evaluate_window(scored_returns)

    assert result["usable"] is True
    assert result["top_beats_median"] is True
    assert result["bottom_at_or_below_median"] is True


def test_evaluate_window_inverted_data_fails_top_condition():
    # Scores inversely correlated with returns -- the top-scoring quartile
    # actually has the worst returns here, so it must fail top_beats_median.
    scored_returns = [(float(i), -float(i) / 1000) for i in range(0, 100, 5)]

    result = evaluate_window(scored_returns)

    assert result["usable"] is True
    assert result["top_beats_median"] is False


def test_evaluate_window_too_few_participants_marked_unusable():
    scored_returns = [(10.0, 0.01), (20.0, 0.02), (30.0, 0.03)]  # only 3

    result = evaluate_window(scored_returns)

    assert result["usable"] is False
    assert "3" in result["reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_hitrate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.backtest.hitrate'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/backtest/hitrate.py`:
```python
"""Quartile-buckets a single window's (score, forward_return) pairs and
checks the release-gate conditions for that window, per
.claude/skills/fintrixa-backtest-methodology."""
import statistics


def evaluate_window(scored_returns: list[tuple[float, float]]) -> dict:
    """scored_returns: list of (technical_score, forward_return) for every
    stock that had enough history/forward-room to participate in this
    window. Requires at least 4 participants (so each quartile has >=1
    stock) -- fewer than that, the window is flagged unusable rather than
    computing a meaningless stat on too few points."""
    n = len(scored_returns)
    if n < 4:
        return {"usable": False, "reason": f"only {n} stocks had data this window, need >=4"}

    ranked = sorted(scored_returns, key=lambda pair: pair[0])
    quartile_size = n // 4
    bottom_quartile = ranked[:quartile_size]
    top_quartile = ranked[-quartile_size:]

    universe_returns = [r for _, r in scored_returns]
    median_return = statistics.median(universe_returns)

    top_mean = statistics.mean(r for _, r in top_quartile)
    bottom_mean = statistics.mean(r for _, r in bottom_quartile)

    return {
        "usable": True,
        "n_participants": n,
        "median_return": median_return,
        "top_quartile_mean": top_mean,
        "bottom_quartile_mean": bottom_mean,
        "top_beats_median": top_mean > median_return,
        "bottom_at_or_below_median": bottom_mean <= median_return,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_hitrate.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/backtest/hitrate.py backend/tests/test_backtest_hitrate.py
git commit -m "feat: add quartile hit-rate window evaluation"
```

---

### Task 4: backtest orchestrator + report

**Files:**
- Create: `backend/app/backtest/report.py`
- Test: `backend/tests/test_backtest_report.py`

**Context:** Tasks 1-3 (done) provide `compute_forward_return`, `generate_rolling_windows`, `replay_technical_score`, `evaluate_window`. This task wires them together against real `DailyPrice`/`Stock` DB rows.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backtest.report import run_backtest
from app.db import Base
from app.models import DailyPrice, Stock


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def _seed_stock_with_history(db, ticker, n_days, start=date(2020, 1, 1), seed=0):
    stock = Stock(ticker=ticker, name=ticker)
    db.add(stock)
    db.flush()

    price = 100.0
    for i in range(n_days):
        price += ((i * 7 + seed * 13) % 11) - 5  # deterministic pseudo-movement
        price = max(price, 1.0)
        db.add(
            DailyPrice(
                stock_id=stock.id,
                trade_date=start + timedelta(days=i),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000.0 + (i % 50),
            )
        )
    db.commit()
    return stock


def test_run_backtest_reports_insufficient_history_when_too_shallow(db_session):
    _seed_stock_with_history(db_session, "AAA.NS", n_days=100)
    _seed_stock_with_history(db_session, "BBB.NS", n_days=100, seed=1)

    report = run_backtest(db_session, horizon_trading_days=21, horizon_label="T+1mo")

    assert report["status"] == "insufficient history"


def test_run_backtest_produces_well_formed_report_with_enough_history(db_session):
    n_days = 200 + 8 * 63 + 63 + 10  # min_history + 8 windows + horizon room + buffer
    for i, ticker in enumerate(["AAA.NS", "BBB.NS", "CCC.NS", "DDD.NS", "EEE.NS", "FFF.NS"]):
        _seed_stock_with_history(db_session, ticker, n_days=n_days, seed=i)

    report = run_backtest(db_session, horizon_trading_days=21, horizon_label="T+1mo")

    assert report["status"] in ("pass", "fail")
    assert report["usable_windows"] >= 8
    assert report["horizon"] == "T+1mo"
    assert "top_quartile_pass_rate" in report
    assert "bottom_quartile_pass_rate" in report
    assert len(report["windows"]) >= 8
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.backtest.report'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/backtest/report.py`:
```python
"""Orchestrates the full backtest run: pulls price history from the DB,
replays the technical score at each rolling window, computes forward
returns, evaluates the release gate, and produces the pass/fail report
per .claude/skills/fintrixa-backtest-methodology's Reporting section."""
import pandas as pd
from sqlalchemy.orm import Session

from app.backtest.forward_returns import compute_forward_return
from app.backtest.hitrate import evaluate_window
from app.backtest.replay import replay_technical_score
from app.backtest.windows import generate_rolling_windows
from app.models import DailyPrice, Stock
from app.scoring.technical import MIN_HISTORY_DAYS

MIN_WINDOWS_REQUIRED = 8
RELEASE_GATE_THRESHOLD = 0.60


def _load_price_series(db: Session) -> dict[str, tuple[pd.Series, pd.Series]]:
    """Returns {ticker: (closes, volumes)}, each a pd.Series indexed by
    trade_date ascending."""
    stocks = db.query(Stock).all()
    series_by_ticker = {}
    for stock in stocks:
        rows = (
            db.query(DailyPrice)
            .filter(DailyPrice.stock_id == stock.id)
            .order_by(DailyPrice.trade_date.asc())
            .all()
        )
        if not rows:
            continue
        dates = [r.trade_date for r in rows]
        closes = pd.Series([r.close for r in rows], index=pd.Index(dates))
        volumes = pd.Series([r.volume for r in rows], index=pd.Index(dates))
        series_by_ticker[stock.ticker] = (closes, volumes)
    return series_by_ticker


def run_backtest(db: Session, horizon_trading_days: int, horizon_label: str) -> dict:
    """Runs the full release-gate backtest for one horizon (e.g. 21
    trading days ~= T+1mo, 63 ~= T+3mo). Returns a report dict with full
    window-by-window evidence -- never a bare pass/fail."""
    series_by_ticker = _load_price_series(db)
    if not series_by_ticker:
        return {
            "horizon": horizon_label,
            "status": "insufficient history",
            "reason": "no price history in DB",
        }

    master_calendar = sorted({d for closes, _ in series_by_ticker.values() for d in closes.index})
    window_dates = generate_rolling_windows(master_calendar, MIN_HISTORY_DAYS, horizon_trading_days)

    window_results = []
    for as_of in window_dates:
        scored_returns = []
        for closes, volumes in series_by_ticker.values():
            replayed = replay_technical_score(closes, volumes, as_of)
            if replayed["score"] is None:
                continue
            forward_return = compute_forward_return(closes, as_of, horizon_trading_days)
            if forward_return is None:
                continue
            scored_returns.append((replayed["score"], forward_return))

        result = evaluate_window(scored_returns)
        result["as_of"] = as_of.isoformat()
        window_results.append(result)

    usable_windows = [w for w in window_results if w["usable"]]
    if len(usable_windows) < MIN_WINDOWS_REQUIRED:
        return {
            "horizon": horizon_label,
            "status": "insufficient history",
            "usable_windows": len(usable_windows),
            "required": MIN_WINDOWS_REQUIRED,
            "windows": window_results,
        }

    top_pass_rate = sum(1 for w in usable_windows if w["top_beats_median"]) / len(usable_windows)
    bottom_pass_rate = sum(1 for w in usable_windows if w["bottom_at_or_below_median"]) / len(usable_windows)
    passed = top_pass_rate >= RELEASE_GATE_THRESHOLD and bottom_pass_rate >= RELEASE_GATE_THRESHOLD

    return {
        "horizon": horizon_label,
        "status": "pass" if passed else "fail",
        "usable_windows": len(usable_windows),
        "top_quartile_pass_rate": round(top_pass_rate, 3),
        "bottom_quartile_pass_rate": round(bottom_pass_rate, 3),
        "windows": window_results,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_backtest_report.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests pass (should be 28 pre-existing + 6 + 2 + 3 + 2 = 41)

- [ ] **Step 6: Commit**

```bash
git add backend/app/backtest/report.py backend/tests/test_backtest_report.py
git commit -m "feat: add backtest orchestrator producing the release-gate report"
```

---

### Task 5: backfill deeper price history

**Files:**
- Create: `backend/scripts/backfill_price_history.py`

**Context:** No unit tests for this script (manual/integration script, same convention as `seed_universe.py` — verified by actually running it, in the next task).

- [ ] **Step 1: Write `backend/scripts/backfill_price_history.py`**

```python
"""One-off backfill: fetches maximum available price history (yfinance
period='max') for every stock already in the DB and persists it.

The regular seed run only fetches 2y (enough for live scoring), but the
backtest methodology needs as much history as free data provides per
ticker for a meaningful number of rolling windows -- see
.claude/skills/fintrixa-backtest-methodology and
docs/superpowers/specs/2026-09-01-backtest-foundation-design.md."""
import time

from app.db import SessionLocal
from app.ingestion.yfinance_client import (
    fetch_price_history,
    normalize_price_history,
    persist_price_history,
)
from app.models import Stock

RATE_LIMIT_DELAY_SECONDS = 0.5


def main():
    db = SessionLocal()
    stocks = db.query(Stock).all()
    print(f"backfilling max price history for {len(stocks)} stocks")

    for stock in stocks:
        history = fetch_price_history(stock.ticker, period="max")
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

        rows = normalize_price_history(history)
        inserted = persist_price_history(db, stock.id, rows)
        db.commit()

        print(f"{stock.ticker}: {len(rows)} rows fetched, {inserted} new rows inserted")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full backend test suite (confirm nothing broke)**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests still pass (this script isn't imported by anything, purely additive)

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/backfill_price_history.py
git commit -m "feat: add price-history backfill script for backtest depth"
```

---

### Task 6: run the backfill and the backtest live, report results

**Files:** none (execution + verification only)

- [ ] **Step 1: Write `backend/scripts/run_backtest.py`**

```python
"""Runs the release-gate backtest for the currently-backtestable horizons
(technical/short-term only -- long-term is blocked on point-in-time
fundamentals not existing on free-tier data, see
docs/superpowers/specs/2026-09-01-backtest-foundation-design.md) and
prints the report per .claude/skills/fintrixa-backtest-methodology's
Reporting section."""
import json

from app.backtest.report import run_backtest
from app.db import SessionLocal

# Trading-day approximations: ~21 trading days/month, ~63/quarter.
HORIZONS = [
    (21, "T+1mo"),
    (63, "T+3mo"),
]


def main():
    db = SessionLocal()
    for horizon_days, label in HORIZONS:
        report = run_backtest(db, horizon_days, label)
        print(f"\n=== {label} ===")
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
```

Commit it:
```bash
git add backend/scripts/run_backtest.py
git commit -m "feat: add CLI to run and print the backtest release-gate report"
```

- [ ] **Step 2: Run the backfill live against the real Postgres**

Run: `cd backend && .venv/bin/python scripts/backfill_price_history.py`
Expected: prints one line per stock with rows fetched/inserted. This hits ~100 live yfinance calls with 0.5s delays each — expect several minutes. Note any tickers that errored (don't silently ignore a crash; if the whole run dies partway, report exactly which ticker and why).

- [ ] **Step 3: Confirm the backfill actually deepened history**

Run: `cd backend && .venv/bin/python -c "
from app.db import SessionLocal
from app.models import DailyPrice
from sqlalchemy import func
db = SessionLocal()
r = db.query(func.min(DailyPrice.trade_date), func.max(DailyPrice.trade_date), func.count(DailyPrice.id)).one()
print('price history range:', r[0], '->', r[1], '| rows:', r[2])
"`
Expected: the date range now spans meaningfully more than the prior ~2 years (large-caps on NSE typically have 10-20+ years available via yfinance) — report the actual before/after range, don't just assert it improved.

- [ ] **Step 4: Run the backtest live and read the actual report**

Run: `cd backend && .venv/bin/python scripts/run_backtest.py`
Expected: prints a report for both T+1mo and T+3mo. Read it — report to the user, verbatim, for each horizon: status (pass/fail/insufficient history), usable_windows count, and if usable, both quartile pass rates. This report IS the deliverable of this stage — do not characterize it as "backtest infrastructure built" without also stating what the actual numbers came out to.

- [ ] **Step 5: If either horizon reports "insufficient history", investigate before concluding**

If the backfill (Step 2-3) didn't actually deepen history enough (e.g. yfinance's `period="max"` returns less than expected for NSE tickers, or there's a bug in window generation), diagnose why — check actual date ranges per stock, check `generate_rolling_windows`'s output length directly against the real master calendar length. Fix any real bug found, re-run Steps 2-4, and only report the final real numbers once the pipeline is confirmed working correctly (a report of "insufficient history" caused by a bug is not the same finding as one caused by genuinely limited free-tier data — distinguish which it is).

- [ ] **Step 6: Record the baseline result in the decisions log**

Add an entry to `docs/DECISIONS.md` (follow the existing entry format: date heading, one-paragraph summary, **Why**, **How to apply**) stating the actual T+1mo and T+3mo release-gate results from Step 4 — this is the first real evidence of whether the current technical formula clears its own bar, and it directly gates whether sub-project C's confidence/holding-period/forecast work (which assumes the formula has *some* predictive signal) is even justified to build next.

```bash
git add docs/DECISIONS.md
git commit -m "docs: record baseline backtest results (T+1mo / T+3mo technical score)"
```
