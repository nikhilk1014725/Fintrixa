# Fintrixa — Tools & External Dependencies

Free-tier tools/libraries this project depends on. Agents should check
here before reaching for something not listed — new dependencies get
added here, not silently installed.

| Tool | Used by | Purpose |
|---|---|---|
| `yfinance` | ingestion | OHLCV price/volume history |
| `nsetools` | ingestion | NSE fundamentals, corporate actions |
| `requests` + `beautifulsoup4` | ingestion | screener.in fallback scrape |
| `pandas` | ingestion, scoring, backtest | data wrangling |
| `pandas-ta` or `ta` | scoring | RSI/MACD/DMA technical indicators |
| `fastapi` + `uvicorn` | api | HTTP layer |
| `sqlalchemy` + `alembic` | api, ingestion | Postgres ORM + migrations |
| `pydantic` | all backend modules | typed interfaces between modules |
| `apscheduler` | api (job runner) | nightly/weekly refresh scheduling |
| `pytest` | all backend modules | testing |
| React + Vite | frontend | dashboard SPA |
| vitest + React Testing Library | frontend | frontend testing |
| Operator's existing Claude access | news_llm | news search + summarization |

No paid data vendor, no paid LLM subscription, no cloud hosting — all
local/free-tier per `docs/DECISIONS.md`. Adding any of those requires
updating this file with the reason, not just installing it.
