# Complete the Technical Trigger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Volume (20pts) and MACD (25pts) components of the Technical Trigger per `docs/superpowers/specs/2026-09-02-complete-technical-trigger-design.md`, then re-run the backtest to see if completing the formula closes the release-gate failure recorded in `docs/DECISIONS.md` (2026-09-02).

**Architecture:** Single-file change to `backend/app/scoring/technical.py` (a scoring-formula change — the backtest gate applies), plus a live re-run of the already-built `backend/backtest` harness. No new modules needed.

**Tech Stack:** Python, pandas, the `ta` library (already a dependency, used for RSI/SMA — this adds its `MACD` class), pytest.

---

### Task 1: implement Volume + MACD components

**Files:**
- Modify: `backend/app/scoring/technical.py`
- Modify: `backend/tests/test_technical.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_technical.py` (keep the two existing tests as-is for now — Step 3 may require adjusting `test_strong_uptrend_scores_high`'s fixture, done in a later step once you can see actual behavior):

```python
def _staircase(n, daily_delta, start=100.0):
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] + daily_delta)
    return pd.Series(prices)


def test_confirming_volume_scores_higher_than_thin_volume_in_identical_uptrend():
    # Same price series both times (isolates the volume component's
    # contribution -- RSI/MA/MACD are identical between the two calls
    # since they only depend on `closes`).
    closes = _staircase(220, daily_delta=0.3)

    thin_volume = pd.Series([1_000_000] * 215 + [500_000] * 5)  # recent volume below its own 20-day average
    confirming_volume = pd.Series([1_000_000] * 215 + [3_000_000] * 5)  # recent volume spikes above average

    thin_result = compute_technical_score(closes, thin_volume)
    confirming_result = compute_technical_score(closes, confirming_volume)

    assert thin_result["score"] is not None
    assert confirming_result["score"] is not None
    assert confirming_result["score"] > thin_result["score"]


def test_confirmed_downtrend_scores_lower_than_thin_volume_downtrend():
    closes = _staircase(220, daily_delta=-0.3)

    thin_volume = pd.Series([1_000_000] * 215 + [500_000] * 5)
    confirming_volume = pd.Series([1_000_000] * 215 + [3_000_000] * 5)

    thin_result = compute_technical_score(closes, thin_volume)
    confirming_result = compute_technical_score(closes, confirming_volume)

    assert thin_result["score"] is not None
    assert confirming_result["score"] is not None
    # confirmed selling pressure (high volume on a downtrend) must score
    # LOWER than an unconfirmed thin-volume drift down -- this is the
    # inverse of the uptrend case above.
    assert confirming_result["score"] < thin_result["score"]


def test_accelerating_uptrend_scores_higher_than_decelerating_uptrend():
    # Both end in positive territory, both above their moving averages --
    # isolates the MACD histogram-direction contribution. Accelerating:
    # slow-then-fast. Decelerating: fast-then-slow (momentum fading even
    # though still technically an uptrend).
    accelerating = pd.concat(
        [_staircase(200, daily_delta=0.1), _staircase(20, daily_delta=1.0, start=120.0)],
        ignore_index=True,
    )
    decelerating = pd.concat(
        [_staircase(200, daily_delta=1.0), _staircase(20, daily_delta=0.1, start=300.0)],
        ignore_index=True,
    )
    volumes = pd.Series([1_000_000] * 220)

    accelerating_result = compute_technical_score(accelerating, volumes)
    decelerating_result = compute_technical_score(decelerating, volumes)

    assert accelerating_result["score"] is not None
    assert decelerating_result["score"] is not None
    assert accelerating_result["score"] > decelerating_result["score"]
```

- [ ] **Step 2: Run tests to verify they fail or reveal current behavior**

Run: `cd backend && .venv/bin/python -m pytest tests/test_technical.py -v -k "confirming or accelerating or confirmed_downtrend"`
Expected: the new tests likely FAIL or the assertions may not hold yet, since `volumes` is currently completely unused by `compute_technical_score` (confirmed in an earlier code review this session) — a change to `volumes` alone currently produces IDENTICAL scores, so `confirming_result["score"] > thin_result["score"]` should fail (they'll be equal). The MACD test may or may not already pass by coincidence via RSI/MA differences alone — note the actual result either way.

- [ ] **Step 3: Write minimal implementation**

Replace the full contents of `backend/app/scoring/technical.py`:

```python
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

MIN_HISTORY_DAYS = 200
VOLUME_MA_WINDOW = 20
MOMENTUM_WINDOW = 5


def compute_technical_score(closes: pd.Series, volumes: pd.Series) -> dict:
    """RSI, 50/200 DMA, Volume, and MACD components of the Technical
    Trigger, per .claude/skills/fintrixa-scoring-formula. All four
    components are now implemented (100 of 100 spec points) -- see
    docs/superpowers/specs/2026-09-02-complete-technical-trigger-design.md
    for the bucket-boundary rationale on the two newly-added components."""
    if len(closes) < MIN_HISTORY_DAYS:
        return {
            "score": None,
            "excluded_reason": (
                f"insufficient price history: {len(closes)} days, "
                f"need >= {MIN_HISTORY_DAYS} for 200-day moving average"
            ),
        }

    rsi = RSIIndicator(close=closes, window=14).rsi().iloc[-1]
    sma50 = SMAIndicator(close=closes, window=50).sma_indicator().iloc[-1]
    sma200 = SMAIndicator(close=closes, window=200).sma_indicator().iloc[-1]
    last_close = closes.iloc[-1]

    # RSI component (0-25 pts): 30-45 or 50-65 scores highest
    if 30 <= rsi <= 45 or 50 <= rsi <= 65:
        rsi_pts = 25.0
    elif 20 <= rsi < 30 or 65 < rsi <= 70:
        rsi_pts = 15.0
    else:
        rsi_pts = 5.0

    # Moving average component (0-30 pts)
    above_both = last_close > sma50 and last_close > sma200
    golden_cross = sma50 > sma200
    if above_both and golden_cross:
        ma_pts = 30.0
    elif above_both:
        ma_pts = 20.0
    elif not golden_cross and last_close < sma50 and last_close < sma200:
        ma_pts = 0.0
    else:
        ma_pts = 10.0

    # Volume component (0-20 pts): above-average volume confirming price
    # direction scores higher than a move on thin volume. Confirmed
    # selling pressure (downtrend + above-average volume) scores lowest --
    # this is a Buy-oriented formula, so confirmed weakness is worse than
    # an unconfirmed drift.
    uptrend = last_close > closes.iloc[-1 - MOMENTUM_WINDOW]
    volume_ma = volumes.rolling(VOLUME_MA_WINDOW).mean().iloc[-1]
    above_avg_volume = volumes.iloc[-1] > volume_ma
    if uptrend and above_avg_volume:
        volume_pts = 20.0
    elif not uptrend and above_avg_volume:
        volume_pts = 0.0
    else:
        volume_pts = 10.0

    # MACD component (0-25 pts): bullish crossover with rising histogram
    # scores highest.
    macd_indicator = MACD(close=closes)
    macd_line = macd_indicator.macd().iloc[-1]
    signal_line = macd_indicator.macd_signal().iloc[-1]
    histogram = macd_indicator.macd_diff()
    bullish = macd_line > signal_line
    rising_histogram = histogram.iloc[-1] > histogram.iloc[-2]
    if bullish and rising_histogram:
        macd_pts = 25.0
    elif bullish:
        macd_pts = 15.0
    elif rising_histogram:
        macd_pts = 10.0
    else:
        macd_pts = 0.0

    # All four components are now implemented -- raw is already 0-100,
    # no scaling needed (the old /55.0*100 scaling is removed).
    score = round(rsi_pts + ma_pts + volume_pts + macd_pts, 1)

    return {"score": score, "excluded_reason": None}
```

- [ ] **Step 4: Run the new tests, verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_technical.py -v`
Expected: the 3 new tests should now pass. If any of the 3 new tests still fails, investigate WHY empirically (print the intermediate `rsi_pts`/`ma_pts`/`volume_pts`/`macd_pts` values in a throwaway debug script if needed) rather than guessing — the fixture deltas/lengths in Step 1 are a reasonable starting point but were not hand-verified against the real `ta` library output. If a fixture needs adjusting to actually produce the intended directional difference, adjust it (keep the test's *intent* — isolating volume, isolating MACD direction — don't weaken the assertion itself).

Also check the 2 pre-existing tests (`test_strong_uptrend_scores_high`, `test_insufficient_history_is_excluded_not_zero`). If `test_strong_uptrend_scores_high` now fails (e.g. its flat constant-volume fixture no longer clears `>=60` because volume_pts lands in the 10pt "unconfirmed" bucket, or MACD histogram plateaus on a purely linear uptrend), adjust that fixture (e.g. add a mild volume increase in the last `VOLUME_MA_WINDOW` days, matching what a genuinely healthy uptrend would look like) so it passes **honestly** under the completed formula — do not lower the `>=60` threshold to paper over an actual behavior change; a linear-uptrend-with-flat-volume is a legitimately weaker signal now that volume is scored, and the fixture should reflect a scenario that deserves a high score, not just historically got one by accident of an incomplete formula.

- [ ] **Step 5: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scoring/technical.py backend/tests/test_technical.py
git commit -m "feat: implement Volume and MACD components of the Technical Trigger"
```

---

### Task 2: re-run the backtest, record the result

**Files:** none (execution + verification only, plus a `docs/DECISIONS.md` entry)

**Context:** The backtest harness (`backend/app/backtest/`, `backend/scripts/run_backtest.py`) already exists and works — Task 1's `replay_technical_score` (in `backend/app/backtest/replay.py`) calls `compute_technical_score` unmodified, so it automatically picks up Task 1's new formula with zero changes needed to the backtest module itself. Price history is already deep enough (backfilled 2026-09-01/02) — no new backfill needed.

- [ ] **Step 1: Run the backtest live with the completed formula**

Run: `cd backend && .venv/bin/python scripts/run_backtest.py > /tmp/backtest_after_volume_macd.json 2>&1`

- [ ] **Step 2: Extract and compare the summary numbers against the 2026-09-02 baseline**

Run something like:
```bash
cd backend && python3 -c "
import json
with open('/tmp/backtest_after_volume_macd.json') as f:
    content = f.read()
parts = content.split('=== ')
for p in parts[1:]:
    label, _, rest = p.partition('\n')
    obj = json.loads(rest)
    print(f\"{label.strip()}: status={obj['status']}, usable_windows={obj.get('usable_windows')}, top_pass_rate={obj.get('top_quartile_pass_rate')}, bottom_pass_rate={obj.get('bottom_quartile_pass_rate')}\")
"
```

Baseline (RSI+MA only, recorded 2026-09-02 in `docs/DECISIONS.md`): T+1mo top=0.655/bottom=0.403 (FAIL), T+3mo top=0.695/bottom=0.364 (FAIL). Compare the new numbers against these directly.

- [ ] **Step 3: Record the result in `docs/DECISIONS.md`**

Add a new dated entry (follow the existing format) stating: the new T+1mo and T+3mo numbers, whether either or both now clear the 60% gate on both conditions, and an explicit statement of whether this formula is now eligible to ship as the live formula (both conditions must pass — a partial improvement that still fails either condition means it stays not-shipped, same as before, per CLAUDE.md's non-negotiable backtest gate). If it still fails, do not attempt further tweaks in this same task — per the design spec, that risks overfitting to this specific backtest window. State plainly what failed and by how much, and that a further change would need its own fresh design/backtest cycle.

```bash
git add docs/DECISIONS.md
git commit -m "docs: record backtest result for completed Technical Trigger (Volume+MACD)"
```

- [ ] **Step 4: Report the outcome plainly**

Whichever way it comes out, state the actual numbers (not just "improved" or "still failing") and what that means for whether sub-project C's confidence/holding-period/forecast work can proceed on this formula.
