---
name: fintrixa-data-sources
description: Use when implementing or modifying backend/ingestion — documents which free data source to use for what, ticker format, fallback order, and rate-limit etiquette to avoid getting blocked.
---

# Fintrixa Data Sources (free tier)

## Price/volume data — yfinance

- Ticker format: NSE = `SYMBOL.NS`, BSE = `SYMBOL.BO`.
- Provides OHLCV history and some fundamentals, but NSE fundamentals
  coverage is inconsistent — treat yfinance fundamentals as
  best-effort, not authoritative.
- Cache responses locally (raw snapshot table) — don't re-fetch the same
  ticker/date range across runs. Batch requests, don't hammer per-ticker
  in tight loops; add jitpath/delay between calls.

## Fundamentals — nsetools, fallback screener.in

- Primary: nsetools for NSE-published fundamentals where available.
- Fallback: screener.in scrape when nsetools/yfinance don't have a
  field. Respect robots.txt and rate limits — this is a shared free
  resource, not an API meant for high-frequency polling. Cache
  aggressively (fundamentals are weekly-refresh per the design spec,
  not per-run).
- Always record which source a fundamental field came from — needed for
  debugging discrepancies and for the raw-snapshot audit trail.

## Corporate actions / announcements — NSE public endpoints

- Board meetings, results dates, announcements: NSE's public archive
  endpoints. Use for the `news_llm` red-flag detection input as well as
  general corporate-action tracking (splits/bonuses affect backtest
  price-adjustment).

## Fallback order (per field)

1. yfinance (fast, but incomplete for NSE fundamentals)
2. nsetools
3. screener.in scrape

If all three fail for a required field, the field is missing — do not
guess or interpolate. Missing-data handling is `scoring`'s job, not
ingestion's; ingestion just reports what it couldn't get and why.

## Rate limiting

- Add delay between sequential requests to the same host.
- Cache every raw response with a timestamp; never re-fetch data younger
  than its scheduled refresh cadence (daily for prices, weekly for
  fundamentals per the design spec).
- If a source starts returning errors/blocks, back off exponentially and
  surface the failure — don't retry in a tight loop.
