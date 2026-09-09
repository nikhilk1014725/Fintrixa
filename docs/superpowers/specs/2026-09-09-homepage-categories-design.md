# Homepage Categories + Card One-Liner — Design Spec
Date: 2026-09-09
Status: Approved

## Purpose
Continues the consumer-UX redesign (`newIdea.md`) on top of the already-shipped
[Phase A](2026-08-31-consumer-ux-phase-a-design.md). Phase A explicitly deferred
two things as "later phases": category sections on the homepage, and showing
the plain-English `explanation` one-liner on the card grid (not just the
detail page). This phase builds those two, still using only fields the API
already computes — no scoring-formula change, no new backend fields.

## Non-negotiable constraints this phase respects
- No scoring-formula change → backtest gate does not apply.
- No silent gaps / no fake enthusiasm: a category section that has zero
  qualifying stocks shows an honest empty-state message, never a padded list.
- No new nav tabs (Watchlist/Profile still deferred, per Phase A).
- Design tokens: lavender/white/black, signal-color exception for verdict
  badges (unchanged).

## API change
`GET /stocks` (list endpoint, `backend/app/api/routes.py`) starts returning
`explanation` — already computed and already returned by the detail endpoint,
just not the list one. Additive field, no schema/DB change, no new test
fixtures needed beyond asserting the field round-trips.

## Homepage — 3 sections (in this order)
1. **Best Today** — stocks where `long_term_label` or `short_term_label` is
   `"Strong Buy"` or `"Buy"`, ranked by whichever score triggered inclusion
   (if both qualify, rank by the higher of the two). Empty state: "No strong
   opportunity today — check back after the next scoring run."
2. **Long-Term Picks** — non-null `long_term_label`, ranked by
   `long_term_score` desc. Empty state if none qualify.
3. **Short-Term Picks** — non-null `short_term_label`, ranked by
   `short_term_score` desc. Empty state if none qualify.

A stock may appear in more than one section if it qualifies for each —
timeframes are independent, hiding the overlap would be misleading.

## Stock card (updated — "Option C" from brainstorming)
Keep both long-term and short-term badges as compact side-by-side pills
(label + score), unchanged from Phase A. Add the `explanation` sentence
underneath both pills. Stocks with no verdict still show `excluded_reason`
in place of badges (unchanged from Phase A — don't touch this path).

## Components touched
- `frontend/src/components/Home.tsx` — replace single sorted grid with the
  3 sections above, each with its own filter/sort/empty-state.
- `frontend/src/components/StockCard.tsx` — render `stock.explanation`
  under the badge row when present.
- `frontend/src/api/client.ts` — add `explanation: string | null` to
  `StockSummary` (it already exists on `StockDetail`).
- `backend/app/api/routes.py` — include `explanation` in the list-endpoint
  response model/query.

## Testing
- `Home.test.tsx`: one case per section (populated), one per section
  (empty), one case for a stock appearing in two sections simultaneously.
- `StockCard.test.tsx`: renders `explanation` when present, omits it when
  null (doesn't render an empty line).
- Backend: extend existing list-endpoint test to assert `explanation` is
  present and matches the detail endpoint's value for the same ticker.

## Explicitly out of scope (tracked for later phases)
Holding period, numeric confidence %, bull/base/bear forecast, additional
categories requiring data not yet computed (Undervalued, Strong Momentum,
Dividend, High Growth, Lower Risk), Watchlist/Profile nav tabs, "I Don't
Know" onboarding quiz, broadening the universe further, NL search, sector
heatmap, portfolio.
