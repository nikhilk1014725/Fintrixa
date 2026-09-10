# Stock Detail Page Redesign — Design Spec
Date: 2026-09-10
Status: Approved

## Purpose

This is Phase 3 of the consumer-UX redesign described in `newIdea.md`
(sections 10–16, 28). Someone with zero stock-market knowledge should be
able to open a stock and understand, in plain words: what the AI thinks,
why, and what could go wrong — without hunting for it behind a "Show
details" toggle.

## Scope decision

`newIdea.md`'s full detail-page vision also wants a suggested holding
period and a bull/base/bear **price** forecast (with % ranges). Neither
exists in the backend today — building them means new scoring/forecasting
logic, which the doc itself lists as separate later phases (8 and 9 in its
build order). This phase only reorganizes and surfaces data that already
exists. No new backend logic, no invented numbers.

## What changes

All changes are in `frontend/src/components/StockDetail.tsx`. No backend
or schema changes — every field used here (`explanation`, `news_bull_case`,
`news_bear_case`, `news_red_flags`, `verdict_override_reason`, price
history) already exists in `StockDetail`/`PriceHistoryPoint`.

### 1. Last close price, shown next to the ticker

Currently the header shows only name + ticker + verdict badges. Add the
most recent price history point's `close` value and `trade_date`, labeled
plainly: `₹1,842 · as of 10 Sep`. If `history` is empty or still loading,
this is simply omitted (no placeholder, no fake "live" framing — it's a
historical close, not a real-time quote).

### 2. "In Simple Words" section (was "Suggested action")

Same content as today (`explanation`, falling back to `excluded_reason`),
just retitled to match the plain-language framing the rest of the redesign
uses. No behavior change.

### 3. "What could go wrong" — merged, always-visible risk section

Today, red flags show as their own top-level card, and the bear case is
hidden behind "Show details." This phase merges them into one section,
visible whenever either exists:

- If `news_red_flags` is non-empty: bullet list of flags (unchanged
  content/styling — still `signal-avoid` red, consistent with the
  Research Digest precedent).
- If `news_bear_case` is non-null: shown as plain text under the same
  section (styled neutral, not red, since a bear case isn't necessarily a
  red flag — it's the researched downside).
- If neither exists, the section doesn't render (no empty-state text here;
  the "In Simple Words" explanation already covers the no-verdict case).

### 4. "What could happen" — bull case promoted to visible

`news_bull_case`, currently hidden behind "Show details," becomes its own
always-visible section (shown only when non-null) — same section title
language as `newIdea.md` section 11 ("What could happen"), scoped for now
to the researched upside narrative only (no bull/base/bear % ranges — see
Scope decision above).

### 5. "Show details" unchanged in purpose, narrower in content

Still holds: score breakdown (fundamental/technical numbers), confidence
tag, and (implicitly, later) sources. Bull/bear case and red flags move
out of this toggle per points 3–4 above — they're core to understanding
the call, not advanced detail.

### 6. Section order on the page

1. Header (name, ticker, last close, verdict badges)
2. In Simple Words
3. What could happen (bull case)
4. What could go wrong (red flags + bear case)
5. Show details toggle → score breakdown + confidence
6. Price history chart (unchanged, stays last)

## Testing

- Header renders last close price + date when history has ≥1 point;
  renders without a price when history is empty or `null`.
- "What could go wrong" section renders when only red flags exist, only
  bear case exists, both exist, and neither exists (doesn't render).
- "What could happen" renders only when `news_bull_case` is non-null.
- "Show details" toggle still shows/hides score breakdown + confidence;
  no longer shows bull/bear case (moved out).
- Existing red-flag-override reason text (`verdict_override_reason`)
  still renders where it does today (under the red flags list).

## Explicitly out of scope

Suggested holding period, bull/base/bear price-percentage forecast, star-
rated sub-scores (business/growth/valuation/momentum), live/real-time
price, "what changed since last analysis," sources & citations UI. These
map to later phases in `newIdea.md`'s own build order (8, 9, and beyond)
and need new backend work first.
