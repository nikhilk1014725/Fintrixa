# Fintrixa

A personal stock-buying guide for Indian equities (NSE). Fintrixa scans a
tracked universe of stocks every day, scores each one on fundamentals and
technicals, and surfaces a plain-English verdict — backed by a backtested
formula and LLM-corroborated news — so a single user can decide what's
worth researching further.

This is a solo-user, free-tier-only project: no paid data vendor, no paid
LLM subscription, one Postgres database, one FastAPI app.

## Tech stack

- **Backend:** Python, FastAPI, PostgreSQL, SQLAlchemy + Alembic, a
  scheduled job (via a local `launchd` job, not an in-process scheduler).
- **Data:** [yfinance](https://pypi.org/project/yfinance/) (`TICKER.NS` /
  `.BO`), NSE's public archive for the tracked universe, screener.in as a
  planned (not yet built) fallback for fields yfinance doesn't expose.
- **Frontend:** React + TypeScript + Vite, Tailwind CSS v4, a small
  lavender/white/black design system.
- **Tests:** pytest (backend), vitest + React Testing Library (frontend).

## Module boundaries (modular monolith)

One FastAPI app, one Postgres database, code split into modules that talk
to each other through typed interfaces — not a microservice split, just
clean internal boundaries:

```
backend/app/ingestion   — pulls the tracked universe + raw market/fundamental data
backend/app/scoring     — fundamental score, technical score, combined verdict
backend/app/backtest    — replays the scoring formula against history; release gate
backend/app/news_llm    — LLM news corroboration + red-flag override, top-N only
backend/app/api         — FastAPI routes, request/response schemas
frontend/               — React dashboard (Home, Discover, Holdings, stock detail)
```

## How a stock gets identified and scored — the full flow

### 1. Universe selection (`backend/app/ingestion/nse_universe.py`)

Every ingestion run fetches NSE's public NIFTY 100 constituent CSV
(`archives.nseindia.com/.../ind_nifty100list.csv`) live — no caching,
since it's ~100 rows and only rebalances twice a year. Each row becomes a
ticker (`SYMBOL.NS`), a name, and a sector. A fetch failure raises loudly
rather than silently seeding an empty universe.

### 2. Raw data fetch (`backend/app/ingestion/yfinance_client.py`)

For each ticker in the universe, Fintrixa pulls:
- **Fundamentals** from `yfinance`'s `.info`: trailing P/E, return on
  equity, debt-to-equity. `sector_pe` is filled in afterwards (see below);
  several other fields (ROCE, revenue/profit CAGR, promoter-holding trend,
  pledged-shares %, auditor changes, negative equity) are not available
  from yfinance today and are left `None` rather than guessed.
- **Price history** (`DailyPrice` rows: OHLCV) for technical scoring and,
  later, the price chart on the stock detail page.

`backend/app/ingestion/enrichment.py`'s `enrich_sector_pe()` fills in
`sector_pe` as the mean trailing P/E across peer stocks in the same
sector from the same ingestion batch — a same-batch approximation, not a
licensed sector-benchmark feed.

### 3. Fundamental score (`backend/app/scoring/fundamental.py`, 0–100)

Requires `trailing_pe`, `sector_pe`, `return_on_equity`, `debt_to_equity`
— if any is missing, the fundamental score is `None` with an explicit
`excluded_reason` (never a guessed/defaulted value). Otherwise, points
are awarded across four buckets, currently scaled from 65 raw points to
100 (growth and promoter-holding components — 35 more raw points — are
speced but not yet implemented, pending data ingestion can't provide
today):

- **Valuation** (0–20): cheaper than sector P/E scores higher.
- **Profitability** (0–20): return-on-equity tiers.
- **Leverage** (0–15): lower debt-to-equity scores higher.
- **Red flags** (0–10, deduction-based): pledged shares, recent auditor
  change, negative equity each dock points.

### 4. Technical score (`backend/app/scoring/technical.py`, 0–100)

Requires ≥200 days of clean price/volume history — otherwise excluded
with an explicit reason (not scored as 0). Four components, all
implemented:

- **RSI** (0–25): 30–45 or 50–65 scores highest (healthy momentum, not
  overbought/oversold extremes).
- **Moving averages** (0–30): price above both the 50- and 200-day SMA
  with a golden cross (50 > 200) scores highest.
- **Volume** (0–20): an uptrend confirmed by above-average volume scores
  highest; a downtrend on above-average volume (confirmed selling
  pressure) scores lowest.
- **MACD** (0–25): a bullish crossover with a rising histogram scores
  highest.

### 5. Combined verdict (`backend/app/scoring/verdict.py`)

```
long_term_score  = 0.7 × fundamental + 0.3 × technical
short_term_score = 0.7 × technical  + 0.3 × fundamental
```

Each score maps independently to a label: **≥80 Strong Buy, ≥60 Buy, ≥40
Hold, else Avoid.** If either sub-score is missing, *both* verdicts are
excluded together (no per-verdict fallback) with a plain-English
`explanation` sentence generated alongside the scores.

**Known limitation, tracked in `docs/DECISIONS.md`:** backtesting has
confirmed the formula reliably identifies future winners (top-quartile
hit rate) but does **not** reliably identify future losers (bottom-
quartile pass rate is no better than chance). Treat "Avoid" as "we don't
have a confident positive case" rather than "predicted to fall."

### 6. Red-flag override (`backend/app/news_llm/override.py`)

If the stock's latest LLM news corroboration (see below) has an active
red flag, any "Strong Buy" or "Buy" label is capped down to "Hold" for
display — the raw score is untouched, only the shown verdict is capped,
and the override reason is always surfaced, never silently applied.

### 7. LLM news corroboration (`backend/app/news_llm/`, top-N only)

To control LLM cost, this step runs only on the top-N stocks by
`long_term_score` (`shortlist.py`), never the full universe. A daily
scheduled routine (a Claude Code CLI job run via `launchd`, not
in-process — see `docs/superpowers/specs/2026-09-02-news-corroboration-
design.md`) researches each shortlisted stock and produces a bull case,
bear case, red flags, a confidence tag (`Corroborated` / `Mixed` /
`Unconfirmed`), and cited sources. `ingest.py` validates the payload
strictly and persists it — a malformed payload is rejected, never
silently coerced.

### 8. Backtest release gate (`backend/app/backtest/`)

No change to the scoring formula ships without passing a hit-rate
threshold check that replays the formula against price history with no
look-ahead bias (`replay.py`, `windows.py`, `forward_returns.py`,
`hitrate.py`, `report.py`). This is enforced as a release gate, not a
nice-to-have — see `.claude/skills/fintrixa-backtest-methodology`.

### 9. API (`backend/app/api/`)

- `GET /stocks` — every tracked stock with its current verdicts, scores,
  and one-line explanation.
- `GET /stocks/{ticker}` — full detail: score breakdown, news
  corroboration fields, red-flag override reason.
- `GET /stocks/{ticker}/history` — OHLCV price history for the chart.
- `POST /holdings`, `GET /holdings` — log a manual buy and grade it
  against the AI verdict that was in effect at the time (see below).

### 10. Frontend (`frontend/`)

- **Home** — three category sections built only from what the API
  actually returns: **Best Today** (Strong Buy/Buy on either timeframe,
  ranked by whichever score qualified), **Long-Term Picks**, **Short-Term
  Picks**. A stock can appear in more than one section; an empty section
  shows an honest "nothing qualifies today" message rather than a padded
  list.
- **Discover** — every tracked stock, including ones excluded from
  scoring (with the reason shown, not hidden).
- **Stock detail** — verdict badges, one-line explanation, price chart,
  and (behind a "Show details" toggle) the full score breakdown and news
  research.
- **My Holdings** — log a manual buy (ticker, price, quantity, date) and
  see current price, gain/loss, and a plain-English read on whether the
  verdict in effect when you bought has held up — a track-record feature,
  not portfolio management.

## Local development

Backend:
```bash
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
brew services start postgresql@16   # if not already running
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.api.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Tests:
```bash
cd backend && .venv/bin/python -m pytest
cd frontend && npm test
```

## Further reading

- `docs/DECISIONS.md` — architecture and product decisions, with the
  reasoning behind each.
- `docs/superpowers/specs/` — design specs for every shipped feature.
- `.claude/skills/fintrixa-scoring-formula` — the exact scoring formula,
  weights, and thresholds.
- `.claude/skills/fintrixa-backtest-methodology` — how the release gate
  works.
- `.claude/skills/fintrixa-data-sources` — which free data source is used
  for what, and the fallback order.
