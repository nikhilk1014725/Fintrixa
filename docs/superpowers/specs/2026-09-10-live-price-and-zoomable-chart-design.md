# Live Price Refresh + Zoomable Chart — Design Spec

Date: 2026-09-10
Status: Approved, ready for implementation plan

## Purpose

Two related stock-detail-page gaps reported by the user:

1. The displayed price is silently stale (latest `DailyPrice` row — end of
   previous trading day at best) with no way to pull a fresher number
   without waiting for the next nightly ingestion run.
2. The price chart always renders full lifetime history with no way to
   zoom into a shorter window.

## Constraint that shapes this whole spec: no free real-time data exists

Researched free/near-free options for NSE/BSE price data before settling
on this design (session research, 2026-09-09/10):

- **yfinance (current source):** ~15 min exchange-delayed by NSE's own
  data-licensing terms — not a network/processing delay, a licensing
  rule. This is a hard floor for anything free.
- **Angel One SmartAPI / Upstox API:** genuinely free real-time
  WebSocket feeds exist, but both require opening and KYC-ing an actual
  brokerage/demat account just to read prices — out of scope for a
  research tool that deliberately isn't a broker. Upstox's free tier is
  also a time-limited promo (through Sep 30, 2026).
- **Scraping NSE's own site directly** (`nseindia.com/api/quote-equity`,
  as used by `nsepython`/similar) — near-real-time, no account needed,
  but **explicitly against NSE's terms of use** (not a gray area) and
  known to be fragile (session/cookie handling breaks periodically).
  User explicitly ruled this out once the ToS conflict was confirmed.
- **Zerodha Kite Connect / Dhan:** market data specifically costs money
  (₹500/mo, ₹499/mo) — free tier is trading-only.

**Decision:** stay on yfinance. Every "current price" and every chart
data point is, and must be labeled as, delayed data — never implied as
live. This is a `CLAUDE.md` correctness requirement (layman-readable,
analytically sound), not just a nicety: showing a stale/delayed number
without saying so would misrepresent what the app actually knows.

## Part A — On-demand price refresh

### What changes

- New lightweight quote fetch, separate from the nightly bulk
  `DailyPrice` ingestion job: fetches one fresh (still ~15-min-delayed —
  that's the data's own floor) quote for a single ticker, on request.
- Stock detail page shows the current price with an explicit
  **"Price as of HH:MM (~15 min delayed)"** label, using the actual
  timestamp of the fetched data point — never "just now," never a bare
  number with no freshness indicator.
- A **Refresh** button triggers this on-demand fetch and updates the
  displayed price + timestamp.

### Backend

- New function in `backend/app/ingestion` (alongside
  `yfinance_client.py`'s existing `fetch_price_history`) — e.g.
  `fetch_latest_quote(ticker) -> {price, as_of}` — a single-ticker,
  single-call yfinance fetch (`Ticker(ticker).history(period="1d",
  interval="1m")` or `fast_info`, whichever yfinance actually returns a
  reliable timestamp for — confirm during implementation, don't assume).
- New API endpoint: `GET /stocks/{ticker}/quote` (`backend/app/api`) —
  returns `{price, as_of}`. Does not write to `DailyPrice` (that table's
  grain is one row per trading day, populated by the existing nightly
  job — this is a separate, ephemeral read, not a new persisted row).
- **Market-hours awareness:** NSE trading hours are 9:15am–3:30pm IST.
  Outside that window, the endpoint returns the last close with a
  `market_closed: true` flag; frontend shows **"Market closed — showing
  last close"** instead of implying a fresher number exists.
- **Rate-limit guardrail:** cooldown of 10 seconds between refreshes per
  session (frontend-enforced via disabling the button; backend does not
  need its own rate limiter for a single-user app, but the frontend
  guard prevents accidental hammering of yfinance on repeated clicks).

### Edge cases

| Case | Behavior |
|---|---|
| yfinance returns no data for the ticker (outage, bad ticker) | Show existing last-known `DailyPrice` value with its own as-of date, and a visible "couldn't refresh" note — never blank the price or silently keep showing a refreshed timestamp that didn't actually refresh |
| Refresh clicked during cooldown | Button disabled, no request sent |
| Market closed | Endpoint and UI both say so explicitly, show last close instead of pretending a live check was made |

## Part B — Zoomable chart

### What changes

Replace the current always-lifetime chart with a **1D / 1W / 1M / 1Y /
MAX** range selector — the standard pattern used by Google Finance/
Robinhood-style apps, rather than exposing "hour" and "minute" as their
own top-level buttons. 1D itself is drawn from intraday bars, so
hour-and-minute-level movement is visible *within* that one view — no
separate buttons needed for granularity that fine.

### Data model

New table `intraday_prices` (new model in `backend/app/models.py`,
Alembic migration following the existing pattern used for
`NewsCorroboration`):

```
intraday_prices
  id            PK
  stock_id      FK -> stocks.id
  timestamp     datetime (exact bar time, not just date)
  price         numeric
  created_at    timestamp
```

Separate table from `DailyPrice`, not a finer-grained replacement for
it — `DailyPrice` continues to serve 1W/1M/1Y/MAX unchanged.

### Ingestion

New periodic job (new script in `backend/scripts`, e.g.
`ingest_intraday_prices.py`, scheduled via the same local-launchd
approach already used for the news-research routine — see
`docs/DECISIONS.md`'s 2026-09-02 entry on why cloud Routines don't work
here, same reasoning applies: needs local Postgres access):

- Runs every 5 minutes during NSE market hours (9:15am–3:30pm IST) on
  trading days.
- For each tracked stock, fetches the latest 5-minute bar
  (`interval="5m"`) and appends one row to `intraday_prices` — does not
  overwrite or deduplicate against existing rows for that timestamp
  (each run only fetches the newest bar).
- **This accumulates permanently in our own DB.** yfinance's own ~60-day
  lookback limit for 5-minute data doesn't matter once we've captured a
  bar — it lives in `intraday_prices` indefinitely, so historical 1D
  views for any day we were actually running this job stay available
  even after yfinance's own window would have expired.
- **Before this job existed:** a 1D chart request for "today" simply has
  no intraday rows yet — fall back to showing only the single
  `DailyPrice` point available (open/close), not an error, not a
  fabricated intraday shape.

### API

- `GET /stocks/{ticker}/history?range=1D|1W|1M|1Y|MAX` (extends the
  existing `GET /stocks/{ticker}/history` endpoint,
  `backend/app/api/routes.py`, which currently takes no params and
  always returns everything).
  - `1D` → queries `intraday_prices` for the current (or most recently
    requested) trading day.
  - `1W`/`1M`/`1Y`/`MAX` → queries `DailyPrice` with the appropriate
    date filter, same table as today, just windowed instead of
    unconditional.
- Default (no `range` param) stays `MAX` for backward compatibility with
  any existing caller.

### Frontend

- `frontend/src/components/StockDetail.tsx`'s `PriceChart` component
  gains a range-selector control (five buttons/tabs: 1D/1W/1M/1Y/MAX)
  above the `recharts` `AreaChart`.
- Selecting a range re-fetches `GET /stocks/{ticker}/history?range=...`
  and re-renders — no client-side slicing of an already-fetched full
  history (avoids ever pulling the whole lifetime dataset just to zoom
  into a day).
- Design system tokens per `.claude/skills/fintrixa-design-system` apply
  to the selector control — no ad-hoc colors.

### Edge cases

| Case | Behavior |
|---|---|
| 1D selected, no intraday data yet for today (job hasn't run, market not open yet, or job just deployed) | Show whatever's available (even just open/prev-close) with a visible "intraday data not yet available" note, not a broken/empty chart with no explanation |
| 1D selected on a non-trading day (weekend/holiday) | Show the most recent trading day's intraday data instead, labeled with that date |
| Ticker has no `DailyPrice` history at all | Existing behavior (excluded/no-data state) — unchanged by this spec |

### Testing

- **Backend unit tests:** `fetch_latest_quote` market-hours branching
  (open vs. closed), intraday ingestion job's append-only behavior
  (doesn't duplicate/overwrite same-timestamp rows), history endpoint's
  range-to-table routing (1D → intraday, others → daily) and date
  windowing math.
- **API tests:** `/quote` endpoint's `market_closed` flag correctness;
  `/history?range=...` returns the right table's data for each range
  value, defaults to MAX with no param.
- **Frontend tests:** range selector re-fetches on change; refresh
  button cooldown disables/re-enables correctly; market-closed and
  no-intraday-yet states render their explicit messages, not blank
  states.

## Module boundaries

- New quote-fetch function and intraday ingestion job: `backend/app/
  ingestion`, following the existing `yfinance_client.py` pattern —
  scoring/API don't reach into yfinance directly.
- New `/quote` and extended `/history` endpoints: `backend/app/api`,
  consuming ingestion through its existing typed interface.
- No changes to `backend/scoring`, `backend/backtest`, or
  `backend/news_llm`.

## Out of scope for this pass

- True real-time data (ruled out — no free, ToS-clean, account-free
  option exists; see constraint section above).
- Separate top-level "hour" / "minute" range buttons (covered by 1D's
  intraday resolution instead).
- Backfilling intraday history for dates before this job is deployed —
  not possible past yfinance's own lookback windows, and not attempted.
- Push/websocket live updates — this is poll-on-demand (refresh button)
  only, not an auto-streaming price.
