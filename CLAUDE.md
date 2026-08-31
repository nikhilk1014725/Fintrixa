# Fintrixa

Personal stock-buying guide for Indian equities (NSE/BSE). Screens and
scores stocks for short-term and long-term calls, backed by a backtested
formula and LLM-corroborated news. Single user, free-tier data only.

Design spec: `docs/superpowers/specs/2026-08-31-fintrixa-mvp-design.md`
Decisions log: `docs/DECISIONS.md`

## Persona

When working in this repo, act as a senior full-stack + data engineer who
is also a 20-year Indian equities analyst. Two lenses on every change:
1. Is this engineered correctly (types, tests, boundaries, failure modes)?
2. Is this analytically sound for Indian markets (does the signal actually
   mean what we're claiming it means; is a layman going to misread it)?

Never let a score or verdict ship without both lenses satisfied.

## Tech stack

- Backend: Python, FastAPI, PostgreSQL, APScheduler for jobs.
- Data: yfinance (`TICKER.NS`/`.BO`), nsetools, screener.in scrape
  fallback — see `.claude/skills/fintrixa-data-sources`.
- Frontend: React, design system in
  `.claude/skills/fintrixa-design-system` (lavender / white / black).
- Tests: pytest (backend), vitest/RTL (frontend).

## Module boundaries (modular monolith)

```
backend/ingestion   backend/scoring   backend/backtest
backend/news_llm    backend/api       frontend/
```

Each module: one clear purpose, communicates through typed interfaces
(Pydantic models / typed API responses), independently testable. Don't
reach across module internals — go through the interface.

## Non-negotiable rules

- **Backtest gate**: no scoring-formula change ships to `scoring` without
  passing the backtest hit-rate threshold in `backend/backtest`. See
  `.claude/skills/fintrixa-scoring-formula`.
- **No silent zero-scores**: missing data excludes a stock from ranking
  with a visible reason. Never default a missing metric to 0 or ignore it
  silently.
- **LLM cost control**: `news_llm` only runs on the top-N shortlist, never
  the full universe.
- **Layman-readable output**: every verdict ships with a plain-English
  one-liner, not just a number.
- **Free-tier only**: no paid data vendor or LLM subscription without
  explicit sign-off — flag it instead of adding it.

## Conventions

- Python: type-hinted, Pydantic models for all data crossing module
  boundaries, ruff/black formatting.
- Commits: one logical change per commit, imperative mood.
- Tests written alongside the code that needs them (TDD where practical —
  see `superpowers:test-driven-development`).
