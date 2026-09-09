# My Holdings Tracker — Design Spec

Date: 2026-09-09
Status: Approved, ready for implementation plan

## Purpose

Let the user manually log a stock buy (ticker, price, quantity, date) and
see, at a glance:

- current price and gain/loss since buy
- whatever AI verdict was on record closest to the buy date
- a plain-English read on whether that call has held up so far

This is a track-record feature, not a portfolio-management feature. It
answers "was the AI right?", not "manage my full holdings." Full
portfolio management (`newIdea.md` §35) stays deprioritized until the
core discovery experience is excellent — this ships a narrow slice ahead
of that, scoped tightly to logging + grading past calls.

## Non-goals (out of scope for this pass)

- Editing or deleting a logged buy
- Partial sells / multiple lots of the same stock merged into one position
- Automatic buy detection (e.g. broker integration, screenshot parsing)
- Linking a buy to one specific recommendation instance — grading works
  off verdict history, not a snapshot captured at click-time

## Data model

New table `holdings`, added the same way `NewsCorroboration` was added
(new model in `backend/app/models.py`, then `alembic revision
--autogenerate`):

```
holdings
  id            PK
  stock_id      FK -> stocks.id
  buy_price     numeric
  quantity      numeric
  buy_date      date
  created_at    timestamp (when the row was logged, not the buy date)
```

No changes to existing tables. Joins against `stocks`, `scores`, and
`daily_prices` exactly the way `Score` and `DailyPrice` already do
(`stock_id` FK).

## Grading logic

New logic, lives in `backend/scoring` (small, isolated module —
`holdings_grading.py` or similar — not mixed into the main scoring
formula code):

1. **Verdict-in-effect lookup:** query `Score` rows for the holding's
   `stock_id` where `computed_at <= buy_date`, take the latest one
   (`ORDER BY computed_at DESC LIMIT 1`). This is "the call in effect
   when you bought."
   - If no such row exists (stock wasn't tracked yet, or bought before
     any research ran): return an explicit `no_call_on_record` state.
     Never fabricate or default to a guessed verdict.
2. **Current price:** latest `DailyPrice` row for the stock.
   - If the latest available price is stale (not today), surface the
     actual date of that price alongside it — never silently label an
     old price as "today's price."
3. **Gain/loss:** `(current_price - buy_price) / buy_price`, using
   `quantity` only to show total ₹ gain/loss, not to change the
   percentage.
4. **Direction comparison:** classify the verdict-in-effect as bullish or
   not (existing label taxonomy: Strong Buy/Buy-type long-term or
   short-term labels count as bullish). Compare against gain/loss sign:
   - bullish verdict + price up → `"Tracking as expected"`
   - bullish verdict + price down → `"Not tracking as expected"`
     (deliberately not "wrong" — long-term calls have multi-year
     horizons; a paper loss early in the window doesn't falsify a
     long-term thesis)
   - no bullish verdict on record (e.g. Hold/Avoid/Watch) → show
     price movement only, no "tracking as expected" framing, since
     there was no bullish call to grade against

## Edge cases (must be visible, never silent — per project's no-silent-
gap rule)

| Case | Behavior |
|---|---|
| Ticker doesn't match any `Stock` row | Reject the entry with a clear "we don't track this stock yet" message at input time, not a silent null downstream |
| No `Score` row before buy date | Show "No AI call on record for this date" instead of a fabricated verdict |
| Latest price data is stale | Show the actual as-of date next to the price, labeled |
| Buy date in the future / before stock's earliest data | Reject at input time with a clear validation message |

## API

New endpoints in `backend/api`, following existing router conventions:

- `POST /holdings` — create a holding (ticker, buy_price, quantity,
  buy_date). Validates ticker exists and buy_date is plausible (not
  future, not before the stock's earliest recorded data).
- `GET /holdings` — list all holdings with computed fields (current
  price, gain/loss, verdict-in-effect, tracking status) — computed at
  read time, not stored, so grading always reflects latest price/score
  data.

Response schema (Pydantic model crossing the api/scoring boundary, per
module-boundary rules): includes the raw holding fields plus a nested
`grading` object with `verdict_in_effect` (nullable), `tracking_status`
(`tracking_as_expected` / `not_tracking_as_expected` / `no_bullish_call` /
`no_call_on_record`), `current_price`, `price_as_of_date`, `gain_loss_pct`,
`gain_loss_abs`.

## Frontend

New "My Holdings" screen, linked from main nav near Watchlist (design
system tokens per `.claude/skills/fintrixa-design-system` — lavender/
white/black, semantic color exception for the tracking-status signal:
green for tracking as expected, yellow/gray for not tracking as expected
or no bullish call, matching the existing Buy/Hold/Avoid color
convention).

- **Add Holding form:** ticker (autocomplete against known stocks), buy
  price, quantity, buy date.
- **Holdings list:** one row per holding — ticker, buy price × quantity,
  current price, gain/loss %, tracking-status line. Tapping a row opens
  the existing stock detail page.
- **Layman-readable rule applies:** the tracking-status line is always a
  plain-English sentence (e.g. "AI called this Strong Long-Term when you
  bought — it's up 12% since then"), never just a status enum shown raw.

## Testing

- **Backend unit tests** (`backend/scoring`): grading logic — nearest-
  verdict lookup (including no-verdict case), direction comparison for
  all four `tracking_status` values, stale-price date surfacing.
- **API tests** (`backend/api`): holding creation validation (unknown
  ticker rejected, future/too-early buy date rejected), list endpoint
  returns correctly computed grading fields.
- **Frontend tests** (vitest/RTL): Add Holding form validation, holdings
  list renders all four tracking-status states distinctly.

## Module boundaries

- `holdings` table/model: `backend/api` owns the CRUD, per existing
  convention (API layer owns its own simple entity tables where no other
  module needs to write them).
- Grading logic: `backend/scoring`, exposed to `api` through a typed
  function/Pydantic response — `api` does not reach into `scoring`
  internals, matching CLAUDE.md's module-boundary rule.
- No changes to `backend/backtest`, `backend/news_llm`, or
  `backend/ingestion`.
