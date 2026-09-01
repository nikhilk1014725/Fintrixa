# Sub-project B — Broader Universe — Design Spec
Date: 2026-09-01
Status: Approved

## Purpose
`newIdea.md` (sub-project B in the decomposition) asks for broader market
coverage than today's 17 hardcoded tickers. Confirmed via live research: NSE
publishes a free, no-auth CSV of NIFTY 100 constituents at
`https://archives.nseindia.com/content/indices/ind_nifty100list.csv` — 100
rows, columns `Company Name,Industry,Symbol,Series,ISIN Code`. Verified live
with a plain browser `User-Agent` header, HTTP 200, no cookies/session
needed. `archives.nseindia.com` works; the main `www.nseindia.com` domain
404s for this path.

Decision (user-approved): NIFTY 100 size, no scan-funnel machinery this
round — nothing in the pipeline is LLM-cost-sensitive yet (`news_llm` and
the forecast engine don't exist), so a lightweight-scan → deep-analysis
funnel would be complexity with no expensive step to gate. Score the whole
fetched universe directly with the existing deterministic formula, same as
today, just ~6x more tickers.

## What changes

### New: `backend/app/ingestion/nse_universe.py`
- `parse_nifty100_csv(csv_text: str) -> list[dict]` — pure function. Uses
  Python's `csv.DictReader` (not naive string splitting — company names can
  contain punctuation). Returns
  `[{"ticker": "RELIANCE.NS", "name": "Reliance Industries Limited",
  "sector": "Oil Gas & Consumable Fuels"}, ...]` — `Symbol` column + `.NS`
  suffix (matches this project's existing NSE ticker convention, e.g.
  `BAJAJ-AUTO.NS` — hyphenated symbols pass through unchanged), `Company
  Name` → `name`, `Industry` → `sector`.
- `fetch_nifty100_constituents() -> list[dict]` — thin network wrapper:
  GETs the CSV with a verified-working browser `User-Agent` header, raises
  on non-200 or network failure (no silent empty-list fallback — an
  ingestion run that can't get the universe should fail loudly, not
  silently seed nothing), passes response text to `parse_nifty100_csv`.
  No caching — the CSV is ~100 rows and NIFTY 100 rebalances only twice a
  year, so re-fetching it every ingestion run is cheap and always current;
  adding a cache layer for this would be premature complexity.

### Modified: `backend/app/ingestion/yfinance_client.py`
- `fetch_fundamentals(ticker: str, sector_hint: str | None = None) -> dict`
  — new optional param. When provided, `sector_hint` (NSE's own Industry
  classification) is used as the `"sector"` field instead of yfinance's
  `info.get("sector")`. NSE's classification is more accurate for Indian
  peer-comparison than yfinance's US-style GICS sector string. Falls back
  to yfinance's sector when `sector_hint` is None (keeps the function
  usable standalone, e.g. for a future single-ticker lookup outside the
  NIFTY 100 batch). Backward compatible — existing callers passing just a
  ticker are unaffected.
- `enrich_sector_pe` (in `enrichment.py`) is **unchanged** — it already
  groups by whatever `"sector"` value is present; it doesn't care where
  that value came from.

### Modified: `backend/scripts/seed_universe.py`
- Hardcoded `TICKERS` list replaced with
  `constituents = fetch_nifty100_constituents()`.
- Fundamentals fetch loop passes `sector_hint=c["sector"]` per constituent.
- Stock upsert uses NSE's `name` (previously the script guessed a name from
  the ticker string, e.g. `"Reliance"` — now `"Reliance Industries
  Limited"`, the authoritative name). If a `Stock` row already exists with
  a different name (from before this change), sync it to the NSE name —
  correctness improvement, not a behavior the frontend depends on
  differently.
- Rate-limit delay unchanged (0.5s between sequential yfinance calls).
  ~100 tickers × ~2 calls (fundamentals + price history) × 0.5s ≈ 100s of
  delay alone, plus request time — a few minutes total, acceptable for a
  weekly/nightly personal batch job per the original design spec's
  scheduling section.
- If `fetch_nifty100_constituents()` raises, the script crashes with that
  error — no try/except swallowing it into an empty run.

## Testing
- `parse_nifty100_csv`: unit test with a small fixture CSV string (header +
  2-3 rows, including one hyphenated symbol like `BAJAJ-AUTO`) — no network
  call.
- `fetch_nifty100_constituents`: test with `requests.get` mocked (via
  `unittest.mock.patch` or `monkeypatch`) — no real network call in the
  test suite. Cover: success path (200 → parsed list), failure path
  (non-200 → raises).
- `fetch_fundamentals`: extend with a test confirming `sector_hint`
  overrides yfinance's sector when provided, and falls back to yfinance's
  sector when not (mock `yf.Ticker` as existing tests presumably do, or
  add the minimal mock needed — check current test coverage for this
  function first, there may be none yet to extend).
- No changes needed to `enrichment.py` tests (function unchanged).
- Manual/integration check: actually run `seed_universe.py` against the
  local Postgres once implemented, confirm real HTTP 200 from the NSE CSV
  endpoint, confirm ~100 stocks land in the DB, confirm sector_pe coverage
  visibly improves (more peers per sector than the old 17-ticker batch).

## Explicitly out of scope
Lightweight-scan/candidate-narrowing funnel (deferred until an expensive
per-stock step — LLM-based news/forecast — actually exists to gate), NIFTY
200 / full-NSE expansion, caching the constituent list, any change to the
scoring formula or `enrichment.py`'s grouping logic itself.
