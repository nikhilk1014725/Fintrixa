# Fintrixa MVP — Design Spec
Date: 2026-08-31
Status: Approved

## Purpose
Personal stock screener for Indian equities (NSE/BSE). Ranks stocks with a
0-100 score, split into a Long-Term verdict and a Short-Term verdict, in
plain language a layman can act on. Single user, free-tier data/APIs only.

## Scope (MVP)
In: screener + score, backtested formula, LLM news corroboration on
shortlist, local web dashboard.
Out (explicitly deferred): multi-user auth, paid data feeds, broadcast/
public hosting, mobile app, order placement/broker integration.

## Architecture — modular monolith
One Python codebase, one FastAPI app, one Postgres DB, one frontend.
Modules are boundary-separated so they can be split into services later
without a rewrite, but nothing is over-engineered for a single user today.

```
Fintrixa/
  backend/
    ingestion/   # pulls + normalizes market data
    scoring/      # fundamental + technical scoring
    backtest/     # historical validation of the scoring formula
    news_llm/     # LLM-based news/sentiment corroboration
    api/          # FastAPI routes
  frontend/        # React dashboard
```

### ingestion
- OHLCV via yfinance (`TICKER.NS` / `.BO`).
- Fundamentals via nsetools + screener.in scrape fallback (P/E, ROE, ROCE,
  D/E, promoter holding, CAGR inputs).
- Corporate actions/announcements from NSE public endpoints.
- Writes raw snapshots (audit trail) + normalized tables (query-friendly).

### scoring
- **Fundamental Score (0-100):** P/E vs sector average, ROE, ROCE, D/E,
  3-5yr revenue/profit CAGR, promoter holding trend, red-flag checks
  (pledged shares, auditor changes, negative equity).
- **Technical Trigger (0-100):** RSI, 50/200 DMA crossover, volume spike,
  MACD.
- **Long-Term Verdict** = 70% fundamental / 30% technical.
- **Short-Term Verdict** = 70% technical / 30% fundamental.
- Verdicts map to layman labels: `Strong Buy / Buy / Hold / Avoid`, plus
  one plain-English sentence explaining why.

### backtest
- Replays the scoring formula over available free historical data
  (~15-20yr for large-caps, less for smaller/newer names).
- Measures forward-return hit-rate per score bucket.
- **Release gate:** scoring changes must clear a minimum hit-rate
  threshold on backtest before they're allowed to serve live scores.

### news_llm
- Runs only on the top-N shortlist (cost control — free-tier budget).
- Searches recent news/filings/analyst commentary, summarizes bull/bear
  case, flags red flags (litigation, downgrades, pledge spikes).
- Confidence tag: `Corroborated / Mixed / Unconfirmed`.
- Uses the operator's existing Claude access; no separate paid LLM
  subscription.

### api + frontend
- FastAPI serves: ranked list (filterable by sector/market-cap/verdict),
  per-stock detail (score breakdown + news summary + price chart).
- Frontend: React dashboard, lavender/white/black design system (see
  `.claude/skills/fintrixa-design-system`).

## Scheduling
- Prices/technicals: nightly, post-market-close.
- Fundamentals: weekly (slow-moving).

## Error handling
- Missing fundamentals → stock excluded from ranking with a visible
  reason, never silently scored as 0.
- Scrape/API failures → retry with backoff; UI shows a stale-data banner
  once data exceeds a freshness threshold.

## Testing
- Unit tests on scoring formulas: fixed input → expected score.
- Backtest hit-rate as an automated release gate before formula changes
  ship live.
- One integration test covering ingestion → score → API on a frozen date
  snapshot.

## Open assumptions (flag if wrong)
- "Free-tier only" for LLM calls means routed through the operator's
  existing Claude access, invoked sparingly (shortlist only), not a
  separate paid subscription.
- Historical depth for backtesting is bounded by what free sources
  (yfinance) actually provide per-ticker; not all stocks will have 20yr
  history.
