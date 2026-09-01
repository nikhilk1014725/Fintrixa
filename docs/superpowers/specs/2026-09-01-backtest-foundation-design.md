# Sub-project C, Stage 1 — Backtest Foundation — Design Spec
Date: 2026-09-01
Status: Approved

## Purpose
Sub-project C (newIdea.md: holding period + confidence + forecast) cannot
be built before `backend/backtest` exists — per CLAUDE.md's non-negotiable
backtest gate, no scoring-formula-derived claim ships without passing the
hit-rate threshold in `.claude/skills/fintrixa-backtest-methodology`.
Confidence/holding-period/forecast are all downstream of "does the scoring
formula's rank order actually predict forward returns" — that's exactly
what the backtest measures. This stage builds that measurement, nothing
downstream of it yet.

## Scope decision: technical-only, this stage
Investigated before designing (see prior turn's findings):
- **Long-term/fundamental backtesting is not currently possible on
  free-tier data.** Fundamentals (P/E, ROE, D/E) are fetched live from
  yfinance and never persisted — there is no point-in-time fundamentals
  table. yfinance only exposes *current* values, not historical-as-of-date
  snapshots. Reconstructing the fundamental score as it would have looked
  at a past date T is not possible without a fundamentals-history data
  source this project doesn't have. **This stage does not attempt it** —
  faking a long-term backtest with today's fundamentals applied
  retroactively would be look-ahead bias, exactly what the methodology's
  checklist forbids.
- **Technical backtesting is possible today.** `compute_technical_score`
  (`backend/app/scoring/technical.py`) is a pure function of a price
  series — slice the series to any historical date T and it replays
  exactly as it would have run live on that date, no look-ahead risk.
- Price history currently held is only 2 years (yfinance default
  `period="2y"` in ingestion) — too shallow for ≥8 independent quarterly
  windows with T+3mo forward-return room. Needs a one-time backfill to
  `period="max"` before a meaningful backtest can run.

**This stage validates the T+1mo and T+3mo (short-term) horizons only.**
Long-term validation stays blocked and explicitly reported as such — not
silently skipped — until a point-in-time fundamentals source exists (a
future sub-project, not scoped here).

## Architecture

### One-time backfill: `backend/scripts/backfill_price_history.py`
Reuses existing `fetch_price_history`/`normalize_price_history`/
`persist_price_history` from `backend/app/ingestion/yfinance_client.py`
with `period="max"` instead of the default `"2y"` — no changes to that
module needed, it's already parameterized. Iterates every `Stock` already
in the DB, same 0.5s rate-limit courtesy delay as `seed_universe.py`. Pure
data pull, no scoring/fundamentals touched — stays within ingestion's
existing contract, just a deeper pull for a different purpose.

### New module: `backend/app/backtest/`
Four small pure/near-pure files (module-boundary rule: single clear
purpose per file) plus an orchestrator:

- **`forward_returns.py`** — `compute_forward_return(closes, as_of,
  horizon_trading_days) -> float | None`. Horizons are expressed in
  **trading days**, not calendar days (T+1mo ≈ 21 trading days, T+3mo ≈ 63)
  — matches the trading-day convention `technical.py` already uses for
  `MIN_HISTORY_DAYS=200`, and avoids weekend/holiday miscounting. Returns
  `None` (never a guessed/interpolated value) if there isn't enough data
  after `as_of` to reach the horizon.
- **`replay.py`** — `replay_technical_score(closes, volumes, as_of) ->
  dict`. Slices both series to `index <= as_of` and calls the *existing*
  `compute_technical_score` unmodified — this is what guarantees no
  look-ahead: the replayed score literally cannot see data after `as_of`.
- **`windows.py`** — `generate_rolling_windows(master_calendar,
  min_history_days, horizon_trading_days) -> list[date]`. Pure function,
  quarterly-spaced (63 trading days) as-of dates bounded so each has room
  for both the history requirement and the forward horizon.
- **`hitrate.py`** — `evaluate_window(scored_returns) -> dict`. Quartile-
  buckets one window's `(score, forward_return)` pairs, checks both
  release-gate conditions (top quartile beats universe median, bottom
  quartile at-or-below median) for that single window. Requires ≥4
  participants (so each quartile has ≥1 stock) or reports the window
  unusable rather than computing a meaningless stat on too few points.
- **`report.py`** — `run_backtest(db, horizon_trading_days, horizon_label)
  -> dict`. Orchestrator: loads every stock's price history from
  `DailyPrice` as a date-indexed `pd.Series`, builds the master trading
  calendar (union of all trade_dates in the DB), generates windows, and
  for each window replays every stock's score + forward return (skipping
  any stock without enough history/forward-room *at that specific
  window* — a newly-listed stock simply contributes fewer windows, it
  isn't excluded from the whole run). Aggregates hit-rate across windows,
  requires ≥8 usable windows (methodology's minimum) or reports
  "insufficient history" rather than a false-confidence number. Applies
  the ≥60% release-gate threshold on both conditions.

### New script: `backend/scripts/run_backtest.py`
Runs `run_backtest` for `(21, "T+1mo")` and `(63, "T+3mo")` — the only
horizons this stage can validate — and prints the full report (per-window
detail, not just pass/fail) per the methodology's Reporting section.
Long-term horizons are not attempted; the script's own docstring states
why, pointing at this spec.

## Testing
- `forward_returns.py`, `windows.py`, `hitrate.py`: pure-function unit
  tests with synthetic data — known start/end prices → known return;
  boundary conditions (as_of missing, insufficient forward room) → `None`;
  window generation bounds; quartile pass/fail on both a clearly-
  discriminating synthetic dataset (expect pass) and a clearly-random one
  (expect plausible fail) plus the `<4` unusable-window case.
- `replay.py`: confirms slicing excludes any date after `as_of` — a
  synthetic series where a huge price spike happens *after* `as_of` must
  not change the replayed score at all.
- `report.py`: integration test against the existing in-memory-sqlite
  fixture pattern (see `backend/tests/test_yfinance_client.py`'s
  `db_session` fixture) with a few synthetic multi-year price series
  seeded directly — not a live network test. Covers: insufficient-history
  case (too little data → reports as such, not a fabricated result), and
  a full run producing a well-formed report with the expected fields.
- Manual/integration check: run the backfill script live, then
  `run_backtest.py` live against the real seeded universe, and actually
  read the resulting report — this stage's deliverable is that report,
  not just green tests.

## Explicitly out of scope this stage
Long-term (T+1yr/T+3yr) backtesting (blocked on point-in-time fundamentals
— a future sub-project). Any confidence score, holding-period
recommendation, or forecast UI (all depend on this stage's report existing
first — YAGNI to build them before knowing whether the current formula
even clears the gate). Any change to the scoring formula itself — this
stage measures the *existing* formula as a baseline; a re-weight is a
separate, later change that would re-run this same harness.
