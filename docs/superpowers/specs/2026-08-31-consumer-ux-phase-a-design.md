# Consumer UX Redesign — Phase A — Design Spec
Date: 2026-08-31
Status: Approved

## Purpose
`newIdea.md` (repo root) proposes redesigning Fintrixa from a research-terminal
UI into a beginner-friendly consumer app. It assumes backend capabilities
(confidence %, holding-period recommendation, bull/base/bear forecast, risk
narrative, sector heatmap, market mood, natural-language search, watchlist
alerts) that do not exist yet — the current backend only computes a
fundamental score, a technical score, and a combined long/short-term verdict
with a one-sentence plain-English explanation.

This phase reskins the existing real data into the new information
architecture. It intentionally does **not** fabricate any field the backend
doesn't compute. That work is decomposed into later phases (B: broaden
universe/scan funnel, C: holding-period + confidence + forecast engine — needs
`backend/backtest` built first since it changes verdict logic, D: news/"what
changed" layer, E: NL search, F: watchlist/alerts, G: sector heatmap). Doc
section H (portfolio) is deferred indefinitely per the doc's own guidance.

## Non-negotiable constraints this phase respects
- No scoring-formula change → backtest gate (`.claude/skills/fintrixa-backtest-methodology`)
  does not apply to this phase. Verdict labels ("Strong Buy"/"Buy"/"Hold"/
  "Avoid") and their score thresholds in `backend/app/scoring/verdict.py`
  are **not modified**. Consumer-friendly labels are a **frontend-only
  display mapping**.
- No silent gaps: every UI element must be backed by a real field from the
  API. No hardcoded universe-size claims ("1,200+ stocks") — copy must read
  the actual count from `/stocks`. No confidence/holding-period/forecast UI
  elements this phase.
- Design tokens: lavender/white/black per
  `.claude/skills/fintrixa-design-system`, semantic-color exception already
  established for verdict badges (green/red).

## Information architecture
Two nav destinations (not four — Watchlist/Profile have no backing yet):

```
Home       — curated view: top-scored stocks as cards ("AI Picks Today")
Discover   — full ranked list (today's RankedTable, restyled as cards)
```

State-based navigation in `App.tsx` (`view: "home" | "discover"`,
`selectedTicker: string | null`), consistent with the existing no-router
decision from the earlier detail-page work.

## Components

### `frontend/src/lib/verdictDisplay.ts` (new)
Pure mapping, no component logic:
```ts
STRONG_BUY -> "Strong Opportunity"
BUY        -> "Potential Opportunity"
HOLD       -> "Worth Watching"
AVOID      -> "No Clear Opportunity"
```
Backend label stays the source of truth (used for badge color variant via
existing `VerdictBadge` → `VARIANT_MAP`); this mapping only changes the
*displayed text*, per doc §36 (don't imply "Buy" as a guarantee).

### `StockCard.tsx` (new)
Replaces table rows with a card (doc §9), built from `StockSummary` fields
only:
- Ticker, name
- AI view: softened label (via `verdictDisplay`) + colored `VerdictBadge`,
  long-term and short-term shown separately (doc §14) — omit the one that's
  null rather than rendering "—"
- One-line explanation is **not** on `StockSummary` today — card shows label
  + score only; full explanation lives on the detail page (existing
  `StockDetail` behavior, unchanged)
- If `excluded_reason` is set instead of a verdict: show the reason in place
  of the badge, same as today's table behavior, not a blank card
- Click → opens detail page (existing `onSelectTicker` wiring)

### `Home.tsx` (new)
- Header: "AI Picks Today"
- Subtext: `Screened from our tracked universe of {stocks.length} Indian stocks.`
  — real count from the `/stocks` response, never a hardcoded number
- Grid of `StockCard` for stocks with a non-null `long_term_label` or
  `short_term_label`, sorted by `long_term_score` desc (fallback
  `short_term_score`)
- Empty state (doc §32) if zero stocks currently have a verdict: "No strong
  opportunities right now. Check back after the next scoring run." — no
  blank grid

### `Discover.tsx` (new, replaces bare `RankedTable` usage in `App.tsx`)
- Same `StockCard` grid, unfiltered, includes excluded stocks (visible
  reason, not hidden) — this is the "see everything" view Home intentionally
  narrows from
- Reuses `fetchStocks()` — no new endpoint

### `StockDetail.tsx` (existing — restructured, not rewritten)
Reorganize into progressive disclosure (doc §28), reusing the existing
`explanation` and score data already fetched:
- **Level 1 (default view)**: name/ticker, verdict badges (softened labels
  via `verdictDisplay`), "Suggested action" card (existing — shows
  `explanation`, falls back to `excluded_reason`), price chart (existing,
  unchanged)
- **Level 2/3 (behind a "Show Details" toggle, collapsed by default)**:
  existing "Score breakdown" card (fundamental/technical tiles + weighting
  note) — this is the raw-numbers section beginners shouldn't see first
- No holding-period, confidence, bull/base/bear, or risk-bullet sections —
  not built this phase, not stubbed with placeholder copy either (keeps the
  page honest about what exists today rather than implying "coming soon"
  clutter)

### `App.tsx` (modified)
- Add `view` state, top nav bar (Home | Discover) using existing header
  structure, route to `Home` / `Discover` / `StockDetail` (detail overlays
  either, same as today)

## Testing
- `verdictDisplay` mapping: unit test all four labels + unknown-label
  fallback.
- `StockCard`: renders label+score, renders `excluded_reason` fallback,
  click fires callback (extends existing `RankedTable.test.tsx` pattern).
- `Home`: renders real universe count in subtext (not hardcoded), renders
  empty state when no stock has a verdict.
- `StockDetail`: Level 2 section hidden by default, toggled open on click
  (extends existing test file).
- No backend tests needed — no backend files touched this phase.

## Explicitly out of scope (tracked for later phases)
Holding period, confidence %, bull/base/bear forecast, risk narrative,
"what changed"/"why today", sector heatmap, market mood, Ask Market AI,
watchlist, alerts, portfolio, onboarding personalization ("I don't know"
flow), broadening the seeded universe past today's 17 tickers.
