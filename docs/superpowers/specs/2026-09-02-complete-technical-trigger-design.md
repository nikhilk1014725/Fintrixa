# Complete the Technical Trigger (Volume + MACD) — Design Spec
Date: 2026-09-02
Status: Approved

## Purpose
The backtest release-gate result (`docs/DECISIONS.md`, 2026-09-02) showed
the current Technical Trigger — RSI (25pts) + Moving Averages (30pts) only,
55 of the spec's 100 points — predicts winners but not losers. The
`.claude/skills/fintrixa-scoring-formula` spec already calls for two more
components that were flagged as "added in the scoring-breadth plan" in
`technical.py`'s own docstring: Volume (20pts) and MACD (25pts). This
implements them, then re-runs the now-working backtest harness to see if
completing the formula closes the gap. This is a scoring-formula change —
the backtest gate applies; it does not ship as the live formula unless it
clears, per CLAUDE.md's non-negotiable rule.

## Component design

The spec gives point weights and qualitative intent; exact bucket
boundaries are an implementation judgment call, same category as the
existing RSI/MA buckets. Documented here for the analytical-soundness
review this persona requires.

### Volume (0-20 pts)
Spec: "Above-average volume confirming price direction scores higher than
a move on thin volume."

- Uptrend signal: `last_close > close 5 trading days ago` (short-momentum
  window, consistent with RSI's own recency).
- Volume signal: `last_volume > 20-day rolling average volume`.
- Buckets:
  - Uptrend + above-average volume → **20pts** (bullish move, confirmed)
  - Uptrend + thin volume → **10pts** (move unconfirmed — could fade)
  - Downtrend + above-average volume → **0pts** (confirmed selling
    pressure — this is a Buy-oriented formula, confirmed weakness is the
    worst case, not a neutral one)
  - Downtrend + thin volume → **10pts** (weak move either way, no strong
    signal, same as the unconfirmed-uptrend case — thin volume means the
    move itself isn't trustworthy regardless of direction)

### MACD (0-25 pts)
Spec: "Bullish crossover with rising histogram scores highest."

Standard MACD (12/26/9 EMA, via the existing `ta` library — already a
project dependency, used for RSI/SMA): `macd_line = EMA12 - EMA26`,
`signal_line = EMA9(macd_line)`, `histogram = macd_line - signal_line`.

- Bullish: `macd_line > signal_line` (currently above signal, i.e. in a
  bullish regime, not requiring the exact crossover bar).
- Rising histogram: `histogram[today] > histogram[yesterday]` (momentum
  building, not just present).
- Buckets:
  - Bullish + rising histogram → **25pts** (spec's explicit "highest" case)
  - Bullish, histogram not rising → **15pts** (bullish but momentum fading)
  - Bearish, histogram rising → **10pts** (early reversal signal, weak but
    not nothing)
  - Bearish, histogram falling → **0pts** (spec's implicit worst case)

### Combined score
With all four components implemented (25+30+20+25 = 100 raw points), the
`raw / 55.0 * 100` scaling in the current code is removed — `raw` IS the
0-100 score directly. `MIN_HISTORY_DAYS = 200` stays unchanged (still the
binding constraint; MACD needs ~35 bars, volume needs 20, both far under
200).

## Testing
- Unit tests for volume and MACD bucket logic with synthetic series
  constructed to hit each of the 4+4 buckets deterministically (known
  price/volume patterns, not reliance on real market data).
- Existing `test_technical.py` tests (`test_strong_uptrend_scores_high`,
  `test_insufficient_history_is_excluded_not_zero`) must still pass —
  adjust the uptrend fixture if needed (e.g. rising volume in the tail) so
  it still clears the `>=60` bar honestly under the completed formula,
  don't just loosen the assertion to force a pass.
- Re-run `backend/scripts/run_backtest.py` live against the already-seeded
  universe (no new backfill needed — same price history serves both
  formulas) for both T+1mo and T+3mo. Report the actual new numbers
  against the 2026-09-02 baseline — this is the point of the whole change.
- If the gate still fails after this, do not reweight further within this
  same change — record the new result in `docs/DECISIONS.md` and flag it
  as a fresh decision point, same as before. Don't chase the gate with ad
  hoc tweaks in one sitting; that's how look-ahead bias and overfitting to
  this specific backtest window creep in.

## Explicitly out of scope
Fundamental score changes (untouched — this is Technical Trigger only).
Growth/promoter-holding components (separate, already-flagged gaps in
`fundamental.py`). Any reweighting of the 70/30 long-term/short-term
combination formula. Confidence/holding-period/forecast work (still
blocked on this gate result, whichever way it comes out).
