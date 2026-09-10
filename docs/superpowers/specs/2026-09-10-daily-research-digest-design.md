# Daily Research Digest — Design Spec
Date: 2026-09-10
Status: Approved

## Purpose

Today, checking what the daily news-research automation found requires
opening each researched stock's detail page one at a time — there is no
single view showing what the whole daily run turned up. This feature adds
a digest screen: every researched stock at a glance (confidence +
red-flag count), filterable by day, with full research history preserved
(nothing is summarized away or discarded).

## Non-negotiable constraints this phase respects

- No scoring-formula change — this only reads existing `NewsCorroboration`
  rows, never touches `backend/app/scoring`.
- No silent gaps: a day with zero researched stocks isn't a possible
  dropdown choice (the dropdown only lists dates that actually have data).
- Design tokens: lavender/white/black, reuses the existing confidence/
  verdict badge styling — no new colors invented.
- LLM cost control unaffected — this is a read-only view over data the
  daily job already produced; it triggers no new LLM calls.

## Data model

No schema change. `NewsCorroboration` already persists every run
(append-only — confirmed: each daily run inserts new rows, never
overwrites), so full history already exists in the database.

## Backend — one new endpoint

`GET /news-digest` in `backend/app/api/routes.py`, returning every
`NewsCorroboration` row ever persisted, joined with its stock's
ticker/name, sorted by `computed_at` descending:

```json
[
  {
    "ticker": "MUTHOOTFIN.NS",
    "name": "Muthoot Finance",
    "computed_at": "2026-09-10T08:25:09Z",
    "confidence": "Corroborated",
    "red_flag_count": 1
  },
  ...
]
```

No query parameters, no date filtering server-side — at this app's scale
(roughly a dozen stocks researched per run), fetching full history and
grouping/filtering by date client-side is simpler than adding a second
"list available dates" endpoint or date-range query params. Revisit if
the table grows large enough that this becomes a real payload-size
problem (not expected for a single-user personal app).

If a stock has more than one `NewsCorroboration` row on the same
calendar date (shouldn't normally happen — one run per day), the
frontend groups by date and keeps only the latest row per stock for that
date, so a stock never appears twice in one day's list.

## Frontend

### New nav tab: "Research"

A 4th tab alongside Home / Discover / Holdings, following the exact same
top-nav pattern already established for those three (`App.tsx`'s
`navButtonClass` + `View` union type).

### Screen behavior

- Fetches `/news-digest` once on first visit to the tab (same lazy-fetch-
  on-first-view pattern as Holdings).
- Groups all rows by calendar date (from `computed_at`).
- Defaults to the **most recent date that has data**.
- A `<select>` dropdown lists only dates that actually have data (derived
  from the fetched rows — never a hardcoded or guessed date), most recent
  first. Changing it re-renders the list for that date, no new fetch.
- Each row: ticker, name, a confidence badge, and a red-flag count badge
  ("2 red flags") shown only when `red_flag_count > 0` — nothing shown
  when there are no flags (not a "0 red flags" badge). **Correction from
  an earlier draft of this spec:** confidence is currently shown as plain
  text on the stock detail page (`StockDetail.tsx:220`, `Confidence:
  {value}`), not an existing badge component — there is nothing to reuse.
  This adds a new confidence badge using the existing `Badge` UI
  primitive (`frontend/src/components/ui/badge.tsx`) with its `neutral`
  variant for all three confidence values (Corroborated/Mixed/
  Unconfirmed) — per the design system, signal colors (green/red) are
  reserved for Buy/Hold/Avoid verdicts specifically, not repurposed for
  a different concept like research confidence, so this stays neutral
  rather than inventing a new color meaning.
- Tapping a row calls `onSelectTicker`, reusing the same navigation wiring
  already used by `Home`, `Discover`, and `Holdings` to open the stock
  detail page — no new navigation concept.
- Empty state (only reachable if the endpoint returns zero rows total,
  e.g. before the automation has ever run): "No research has been logged
  yet."

## Testing

- Backend: `GET /news-digest` returns the joined shape (ticker, name,
  computed_at, confidence, red_flag_count) sorted descending by
  `computed_at`; a stock with an empty `red_flags` list returns
  `red_flag_count: 0`; a stock with no `NewsCorroboration` row at all is
  simply absent from the response (not a null-filled row).
- Frontend: date-grouping picks the correct distinct dates for the
  dropdown; defaults to the most recent date on first render; switching
  the dropdown re-renders the correct subset without a new fetch; the
  red-flag badge appears only when count > 0; a stock appearing twice on
  the same date in the raw API response collapses to one row (latest
  wins); tapping a row calls `onSelectTicker` with the right ticker; empty
  state renders when there's no data at all.

## Explicitly out of scope

Date-range filtering (e.g. "last 7 days"), search/sort beyond the date
dropdown, showing bull/bear case text inline in the digest (stays on the
stock detail page), any change to how or when the daily research job
itself runs.
