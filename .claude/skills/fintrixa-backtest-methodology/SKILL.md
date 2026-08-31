---
name: fintrixa-backtest-methodology
description: Use when implementing or modifying backend/backtest — defines how the scoring formula is validated against history and the release-gate threshold that must pass before a scoring change ships.
---

# Fintrixa Backtest Methodology

## What gets tested

Replay the scoring formula as-of each historical date T (using only data
that existed at T — no look-ahead), bucket stocks into quartiles by
score, then measure forward returns from T.

- **Short-term buckets**: forward return at T+1mo and T+3mo.
- **Long-term buckets**: forward return at T+1yr and T+3yr.

## Rolling windows

Use rolling test windows (e.g. quarterly re-scoring points) across as
much history as free data provides per ticker. Require a minimum of 8
independent windows before a hit-rate is considered meaningful — report
"insufficient history" rather than a false-confidence number if fewer
are available.

## Release gate (must pass to ship a scoring change)

- Top-quartile bucket's average forward return beats the full-universe
  median forward return in **≥ 60%** of rolling windows, for both the
  short-term and long-term horizon being changed.
- Bottom-quartile (Avoid) bucket's average forward return must be **at or
  below** the full-universe median in the same proportion of windows —
  the formula has to actually discriminate at the bottom too, not just
  the top.
- If either condition fails, the change is rejected — report which
  windows/horizons failed and by how much, don't just say "failed."

## Look-ahead bias checklist

Before trusting any backtest result, confirm:
- Fundamentals used at T reflect only filings that were public as of T
  (reporting lag matters — a quarter's results aren't known the day the
  quarter ends).
- Technical indicators use only price/volume data up to and including T.
- Corporate actions (splits/bonuses) are adjusted consistently in both
  the scoring input and the forward-return calculation.

## Reporting

Every backtest run produces a report: pass/fail per horizon, per-window
hit-rate, and the specific buckets/windows that drove a failure. This
report is the evidence the `qa-agent` checks for before considering a
scoring change done — a claim of "backtested" without this report is not
sufficient.
