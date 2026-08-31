# Fintrixa Walking Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the full loop — ingest one real NSE stock's price+fundamental
data, score it with the complete formula from `.claude/skills/fintrixa-scoring-formula`,
serve it via FastAPI, and render it on a lavender/white/black React dashboard —
before fanning breadth work (more tickers, backtest, news) out to parallel
module agents.

**Architecture:** Modular monolith per `docs/superpowers/specs/2026-08-31-fintrixa-mvp-design.md`.
This plan builds `backend/ingestion` (price + yfinance-`.info` fundamentals
only, single ticker), `backend/scoring` (full formula), `backend/api`
(list + detail routes), and `frontend/` (ranked table + verdict badge) —
enough to lock the interfaces every other module builds against. `backtest`
and `news_llm` are deliberately out of scope here: both need multi-ticker,
multi-window history to do anything real, and are covered by their own
plans once this skeleton's contracts are stable (see "Next" at the bottom).

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 + Alembic, PostgreSQL,
Pydantic v2, pytest, yfinance, pandas, `ta`, ruff — React + TypeScript +
Vite, vitest + React Testing Library.

---

## Task 0: Backend project scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/.gitignore`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "fintrixa-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "yfinance>=0.2.40",
    "pandas>=2.2",
    "ta>=0.11.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0", "ruff>=0.5", "httpx>=0.27"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `backend/app/__init__.py`** (empty file)

- [ ] **Step 3: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://fintrixa:fintrixa@localhost:5432/fintrixa"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: Create `backend/tests/__init__.py`** (empty file)

- [ ] **Step 5: Create `backend/.gitignore`**

```
__pycache__/
*.pyc
.venv/
.env
```

- [ ] **Step 6: Install and verify**

Run:
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -c "from app.config import settings; print(settings.database_url)"
```
Expected: prints the default database URL, no import errors.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/app/config.py backend/tests/__init__.py backend/.gitignore
git commit -m "chore: scaffold backend project"
```

---

## Task 1: Database models + migration

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`

- [ ] **Step 1: Create `backend/app/db.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Create `backend/app/models.py`**

```python
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))

    daily_prices: Mapped[list["DailyPrice"]] = relationship(back_populates="stock")
    scores: Mapped[list["Score"]] = relationship(back_populates="stock")


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    stock: Mapped["Stock"] = relationship(back_populates="daily_prices")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    fundamental_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    long_term_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    short_term_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    long_term_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    short_term_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    excluded_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="scores")
```

- [ ] **Step 3: Init alembic**

Run:
```bash
cd backend && alembic init alembic
```

- [ ] **Step 4: Edit `backend/alembic/env.py`** — add after the existing imports, before `target_metadata = None`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db import Base
from app import models  # noqa: F401 — registers models on Base.metadata

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

- [ ] **Step 5: Generate migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "initial schema"
```
Expected: creates `backend/alembic/versions/<hash>_initial_schema.py` with
`create_table` for `stocks`, `daily_prices`, `scores`.

- [ ] **Step 6: Apply migration and verify**

Run:
```bash
cd backend && alembic upgrade head
psql "$DATABASE_URL" -c "\dt"
```
Expected: lists `stocks`, `daily_prices`, `scores`, `alembic_version` tables.

- [ ] **Step 7: Commit**

```bash
git add backend/app/db.py backend/app/models.py backend/alembic.ini backend/alembic/
git commit -m "feat: add database models and initial migration"
```

---

## Task 2: Ingestion — price history for one ticker

**Files:**
- Create: `backend/app/ingestion/__init__.py`
- Create: `backend/app/ingestion/yfinance_client.py`
- Test: `backend/tests/test_yfinance_client.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_yfinance_client.py`

```python
import pandas as pd

from app.ingestion.yfinance_client import normalize_price_history


def test_normalize_price_history_maps_expected_columns():
    raw = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [104.0],
            "Volume": [123456.0],
        },
        index=pd.to_datetime(["2026-08-28"]),
    )

    rows = normalize_price_history(raw)

    assert rows == [
        {
            "trade_date": "2026-08-28",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 123456.0,
        }
    ]


def test_normalize_price_history_empty_input_returns_empty_list():
    assert normalize_price_history(pd.DataFrame()) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_yfinance_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion'`

- [ ] **Step 3: Create `backend/app/ingestion/__init__.py`** (empty file)

- [ ] **Step 4: Create `backend/app/ingestion/yfinance_client.py`**

```python
import pandas as pd
import yfinance as yf


def fetch_price_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Fetch daily OHLCV history for an NSE/BSE ticker, e.g. 'RELIANCE.NS'."""
    return yf.Ticker(ticker).history(period=period)


def normalize_price_history(raw: pd.DataFrame) -> list[dict]:
    if raw.empty:
        return []

    rows = []
    for trade_date, row in raw.iterrows():
        rows.append(
            {
                "trade_date": trade_date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            }
        )
    return rows


def fetch_fundamentals(ticker: str) -> dict:
    """Best-effort fundamentals from yfinance .info — incomplete for many
    NSE tickers. screener.in fallback is added in the ingestion-breadth
    plan; this returns whatever yfinance has, with explicit None for the
    rest so callers never mistake missing for zero."""
    info = yf.Ticker(ticker).info
    return {
        "trailing_pe": info.get("trailingPE"),
        "sector_pe": None,  # not available from yfinance; breadth plan adds sector-avg calc
        "return_on_equity": info.get("returnOnEquity"),
        "return_on_capital_employed": None,  # not exposed by yfinance
        "debt_to_equity": info.get("debtToEquity"),
        "revenue_cagr_3y": None,  # requires multi-year financials; breadth plan
        "profit_cagr_3y": None,
        "promoter_holding_trend": None,  # not available from yfinance
        "pledged_shares_pct": None,
        "auditor_changed_recently": None,
        "negative_equity": None,
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_yfinance_client.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/ backend/tests/test_yfinance_client.py
git commit -m "feat: fetch and normalize price history via yfinance"
```

---

## Task 3: Scoring — technical score (RSI + DMA cross)

**Files:**
- Create: `backend/app/scoring/__init__.py`
- Create: `backend/app/scoring/technical.py`
- Test: `backend/tests/test_technical.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_technical.py`

```python
import pandas as pd

from app.scoring.technical import compute_technical_score


def _uptrend_prices(n=260, start=100.0, step=0.3):
    return pd.Series([start + step * i for i in range(n)])


def test_strong_uptrend_scores_high():
    closes = _uptrend_prices()
    volumes = pd.Series([1_000_000] * len(closes))

    result = compute_technical_score(closes, volumes)

    assert result["score"] >= 60
    assert result["excluded_reason"] is None


def test_insufficient_history_is_excluded_not_zero():
    closes = pd.Series([100.0, 101.0, 102.0])  # far short of 200-day window
    volumes = pd.Series([1_000_000, 1_000_000, 1_000_000])

    result = compute_technical_score(closes, volumes)

    assert result["score"] is None
    assert "insufficient" in result["excluded_reason"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_technical.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scoring'`

- [ ] **Step 3: Create `backend/app/scoring/__init__.py`** (empty file)

- [ ] **Step 4: Create `backend/app/scoring/technical.py`**

```python
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

MIN_HISTORY_DAYS = 200


def compute_technical_score(closes: pd.Series, volumes: pd.Series) -> dict:
    """RSI + 50/200 DMA components of the Technical Trigger, per
    .claude/skills/fintrixa-scoring-formula. Volume and MACD components
    are added in the scoring-breadth plan; this covers the two components
    that most directly need price history depth, to prove the exclusion
    rule works before adding the rest."""
    if len(closes) < MIN_HISTORY_DAYS:
        return {
            "score": None,
            "excluded_reason": (
                f"insufficient price history: {len(closes)} days, "
                f"need >= {MIN_HISTORY_DAYS} for 200-day moving average"
            ),
        }

    rsi = RSIIndicator(close=closes, window=14).rsi().iloc[-1]
    sma50 = SMAIndicator(close=closes, window=50).sma_indicator().iloc[-1]
    sma200 = SMAIndicator(close=closes, window=200).sma_indicator().iloc[-1]
    last_close = closes.iloc[-1]

    # RSI component (0-25 pts): 30-45 or 50-65 scores highest
    if 30 <= rsi <= 45 or 50 <= rsi <= 65:
        rsi_pts = 25.0
    elif 20 <= rsi < 30 or 65 < rsi <= 70:
        rsi_pts = 15.0
    else:
        rsi_pts = 5.0

    # Moving average component (0-30 pts)
    above_both = last_close > sma50 and last_close > sma200
    golden_cross = sma50 > sma200
    if above_both and golden_cross:
        ma_pts = 30.0
    elif above_both:
        ma_pts = 20.0
    elif not golden_cross and last_close < sma50 and last_close < sma200:
        ma_pts = 0.0
    else:
        ma_pts = 10.0

    # Scaled to 0-100 using only the two implemented components (55 pts max)
    # until volume/MACD land in the breadth plan.
    raw = rsi_pts + ma_pts
    score = round((raw / 55.0) * 100, 1)

    return {"score": score, "excluded_reason": None}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_technical.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/scoring/__init__.py backend/app/scoring/technical.py backend/tests/test_technical.py
git commit -m "feat: compute technical score from RSI and moving averages"
```

---

## Task 4: Scoring — fundamental score

**Files:**
- Create: `backend/app/scoring/fundamental.py`
- Test: `backend/tests/test_fundamental.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_fundamental.py`

```python
from app.scoring.fundamental import compute_fundamental_score


def test_strong_fundamentals_score_high():
    result = compute_fundamental_score(
        {
            "trailing_pe": 15.0,
            "sector_pe": 25.0,
            "return_on_equity": 0.22,
            "debt_to_equity": 0.1,
            "pledged_shares_pct": 0.0,
            "auditor_changed_recently": False,
            "negative_equity": False,
        }
    )
    assert result["score"] >= 60
    assert result["excluded_reason"] is None


def test_missing_required_field_excludes_not_zeroes():
    result = compute_fundamental_score(
        {
            "trailing_pe": None,
            "sector_pe": 25.0,
            "return_on_equity": 0.22,
            "debt_to_equity": 0.1,
            "pledged_shares_pct": 0.0,
            "auditor_changed_recently": False,
            "negative_equity": False,
        }
    )
    assert result["score"] is None
    assert "trailing_pe" in result["excluded_reason"]


def test_pledged_shares_deduct_red_flag_points():
    base = dict(
        trailing_pe=15.0,
        sector_pe=25.0,
        return_on_equity=0.22,
        debt_to_equity=0.1,
        pledged_shares_pct=0.0,
        auditor_changed_recently=False,
        negative_equity=False,
    )
    clean = compute_fundamental_score(base)
    pledged = compute_fundamental_score({**base, "pledged_shares_pct": 0.15})
    assert pledged["score"] < clean["score"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fundamental.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create `backend/app/scoring/fundamental.py`**

```python
REQUIRED_FIELDS = [
    "trailing_pe",
    "sector_pe",
    "return_on_equity",
    "debt_to_equity",
]


def compute_fundamental_score(data: dict) -> dict:
    """Valuation, profitability, leverage, red-flags components of the
    Fundamental Score, per .claude/skills/fintrixa-scoring-formula.
    Growth and promoter-holding components need multi-year data not yet
    fetched by ingestion — added in the ingestion-breadth plan alongside
    scoring's corresponding component."""
    missing = [f for f in REQUIRED_FIELDS if data.get(f) is None]
    if missing:
        return {
            "score": None,
            "excluded_reason": f"missing required fundamental fields: {', '.join(missing)}",
        }

    # Valuation (0-20 pts): cheaper than sector scores higher
    pe_ratio = data["trailing_pe"] / data["sector_pe"]
    if pe_ratio <= 0.7:
        valuation_pts = 20.0
    elif pe_ratio <= 1.0:
        valuation_pts = 14.0
    elif pe_ratio <= 1.3:
        valuation_pts = 7.0
    else:
        valuation_pts = 2.0

    # Profitability (0-20 pts): ROE only implemented here (ROCE needs a
    # field yfinance doesn't expose — added in ingestion-breadth plan)
    roe = data["return_on_equity"]
    if roe >= 0.20:
        profitability_pts = 20.0
    elif roe >= 0.12:
        profitability_pts = 13.0
    elif roe >= 0.05:
        profitability_pts = 6.0
    else:
        profitability_pts = 0.0

    # Leverage (0-15 pts)
    de = data["debt_to_equity"]
    if de <= 0.2:
        leverage_pts = 15.0
    elif de <= 0.6:
        leverage_pts = 10.0
    elif de <= 1.2:
        leverage_pts = 5.0
    else:
        leverage_pts = 0.0

    # Red flags (0-10 pts, deduction-based)
    red_flag_pts = 10.0
    if data.get("pledged_shares_pct", 0) and data["pledged_shares_pct"] > 0.10:
        red_flag_pts -= 5.0
    if data.get("auditor_changed_recently"):
        red_flag_pts -= 3.0
    if data.get("negative_equity"):
        red_flag_pts -= 10.0
    red_flag_pts = max(red_flag_pts, 0.0)

    # Scaled to 0-100 using the 65 pts currently implemented (valuation
    # 20 + profitability 20 + leverage 15 + red-flags 10) until growth
    # (20) and promoter-holding (15) land.
    raw = valuation_pts + profitability_pts + leverage_pts + red_flag_pts
    score = round((raw / 65.0) * 100, 1)

    return {"score": score, "excluded_reason": None}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fundamental.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/scoring/fundamental.py backend/tests/test_fundamental.py
git commit -m "feat: compute fundamental score from valuation, profitability, leverage, red flags"
```

---

## Task 5: Scoring — combined verdict + label + explanation

**Files:**
- Create: `backend/app/scoring/verdict.py`
- Test: `backend/tests/test_verdict.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_verdict.py`

```python
from app.scoring.verdict import combine_scores


def test_strong_buy_long_term_weights_fundamentals_more():
    result = combine_scores(fundamental_score=90.0, technical_score=40.0)
    # 0.7*90 + 0.3*40 = 75 -> Buy
    assert result["long_term_label"] == "Buy"
    assert result["long_term_score"] == 75.0


def test_strong_buy_short_term_weights_technical_more():
    result = combine_scores(fundamental_score=40.0, technical_score=90.0)
    # 0.3*40 + 0.7*90 = 75 -> Buy
    assert result["short_term_label"] == "Buy"
    assert result["short_term_score"] == 75.0


def test_missing_either_score_excludes_both_verdicts():
    result = combine_scores(fundamental_score=None, technical_score=90.0)
    assert result["long_term_score"] is None
    assert result["long_term_label"] is None
    assert result["short_term_score"] is None
    assert "fundamental" in result["excluded_reason"]


def test_label_thresholds():
    assert combine_scores(85.0, 85.0)["long_term_label"] == "Strong Buy"
    assert combine_scores(65.0, 65.0)["long_term_label"] == "Buy"
    assert combine_scores(45.0, 45.0)["long_term_label"] == "Hold"
    assert combine_scores(20.0, 20.0)["long_term_label"] == "Avoid"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_verdict.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create `backend/app/scoring/verdict.py`**

```python
def _label(score: float) -> str:
    if score >= 80:
        return "Strong Buy"
    if score >= 60:
        return "Buy"
    if score >= 40:
        return "Hold"
    return "Avoid"


def combine_scores(fundamental_score: float | None, technical_score: float | None) -> dict:
    """Combines the two sub-scores per .claude/skills/fintrixa-scoring-formula:
    Long-Term = 70% fundamental / 30% technical, Short-Term = 70% technical
    / 30% fundamental. Missing either input excludes both verdicts rather
    than defaulting the missing one to a neutral value."""
    if fundamental_score is None or technical_score is None:
        missing = []
        if fundamental_score is None:
            missing.append("fundamental score")
        if technical_score is None:
            missing.append("technical score")
        return {
            "long_term_score": None,
            "short_term_score": None,
            "long_term_label": None,
            "short_term_label": None,
            "explanation": None,
            "excluded_reason": f"missing {' and '.join(missing)}",
        }

    long_term = round(0.7 * fundamental_score + 0.3 * technical_score, 1)
    short_term = round(0.7 * technical_score + 0.3 * fundamental_score, 1)
    long_term_label = _label(long_term)
    short_term_label = _label(short_term)

    explanation = (
        f"Long-term: {long_term_label.lower()} on fundamentals "
        f"({fundamental_score:.0f}/100) with technicals at "
        f"{technical_score:.0f}/100. Short-term: {short_term_label.lower()} "
        f"on current momentum."
    )

    return {
        "long_term_score": long_term,
        "short_term_score": short_term,
        "long_term_label": long_term_label,
        "short_term_label": short_term_label,
        "explanation": explanation,
        "excluded_reason": None,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_verdict.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/scoring/verdict.py backend/tests/test_verdict.py
git commit -m "feat: combine fundamental and technical scores into long/short-term verdicts"
```

---

## Task 6: API — Pydantic schemas + routes

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/app/api/main.py`
- Test: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_routes.py`

```python
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.db import Base, get_db
from app.models import Score, Stock


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestSession()
    stock = Stock(ticker="RELIANCE.NS", name="Reliance Industries")
    db.add(stock)
    db.flush()
    db.add(
        Score(
            stock_id=stock.id,
            computed_at=datetime(2026, 8, 31, 18, 0, 0),
            fundamental_score=82.0,
            technical_score=70.0,
            long_term_score=78.4,
            short_term_score=73.6,
            long_term_label="Buy",
            short_term_label="Buy",
            explanation="Long-term: buy on fundamentals (82/100)...",
            excluded_reason=None,
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_list_stocks_returns_latest_scores(client):
    response = client.get("/stocks")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "RELIANCE.NS"
    assert body[0]["long_term_label"] == "Buy"


def test_stock_detail_returns_full_breakdown(client):
    response = client.get("/stocks/RELIANCE.NS")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "RELIANCE.NS"
    assert body["fundamental_score"] == 82.0
    assert body["technical_score"] == 70.0


def test_stock_detail_unknown_ticker_returns_404(client):
    response = client.get("/stocks/NOPE.NS")
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.api'`

- [ ] **Step 3: Create `backend/app/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel


class StockSummary(BaseModel):
    ticker: str
    name: str
    long_term_label: str | None
    short_term_label: str | None
    long_term_score: float | None
    short_term_score: float | None
    computed_at: datetime | None
    excluded_reason: str | None

    class Config:
        from_attributes = True


class StockDetail(StockSummary):
    fundamental_score: float | None
    technical_score: float | None
    explanation: str | None
```

- [ ] **Step 4: Create `backend/app/api/__init__.py`** (empty file)

- [ ] **Step 5: Create `backend/app/api/routes.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Score, Stock
from app.schemas import StockDetail, StockSummary

router = APIRouter()


def _latest_score(db: Session, stock: Stock) -> Score | None:
    stmt = (
        select(Score)
        .where(Score.stock_id == stock.id)
        .order_by(Score.computed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


@router.get("/stocks", response_model=list[StockSummary])
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.execute(select(Stock)).scalars().all()
    results = []
    for stock in stocks:
        score = _latest_score(db, stock)
        results.append(
            StockSummary(
                ticker=stock.ticker,
                name=stock.name,
                long_term_label=score.long_term_label if score else None,
                short_term_label=score.short_term_label if score else None,
                long_term_score=score.long_term_score if score else None,
                short_term_score=score.short_term_score if score else None,
                computed_at=score.computed_at if score else None,
                excluded_reason=score.excluded_reason if score else "not yet scored",
            )
        )
    return results


@router.get("/stocks/{ticker}", response_model=StockDetail)
def stock_detail(ticker: str, db: Session = Depends(get_db)):
    stock = db.execute(select(Stock).where(Stock.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"unknown ticker: {ticker}")

    score = _latest_score(db, stock)
    return StockDetail(
        ticker=stock.ticker,
        name=stock.name,
        long_term_label=score.long_term_label if score else None,
        short_term_label=score.short_term_label if score else None,
        long_term_score=score.long_term_score if score else None,
        short_term_score=score.short_term_score if score else None,
        fundamental_score=score.fundamental_score if score else None,
        technical_score=score.technical_score if score else None,
        computed_at=score.computed_at if score else None,
        explanation=score.explanation if score else None,
        excluded_reason=score.excluded_reason if score else "not yet scored",
    )
```

- [ ] **Step 6: Create `backend/app/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="Fintrixa API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && pytest tests/test_routes.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/api/ backend/tests/test_routes.py
git commit -m "feat: add FastAPI routes for stock list and detail"
```

---

## Task 7: Frontend scaffold + design tokens

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "fintrixa-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^24.1.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: Create `frontend/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

- [ ] **Step 3: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>Fintrixa</title>
    <link rel="stylesheet" href="/src/styles/tokens.css" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `frontend/src/styles/tokens.css`** (per `.claude/skills/fintrixa-design-system`)

```css
:root {
  --lavender-50: #f5f2fb;
  --lavender-100: #e8e1f5;
  --lavender-300: #c3afe8;
  --lavender-500: #8e6fd1;
  --lavender-700: #5f45a3;
  --lavender-900: #362566;

  --white: #ffffff;
  --off-white: #faf9fc;
  --black: #0b0a0f;
  --ink-900: #17151f;
  --ink-600: #4b4759;
  --ink-400: #85809a;
  --border: #e3deee;
  --border-dark: #2b2735;

  --signal-strong-buy: #2f9e63;
  --signal-buy: #6fb98f;
  --signal-hold: var(--lavender-300);
  --signal-avoid: #c1473b;

  --bg: var(--off-white);
  --text: var(--ink-900);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: var(--black);
    --text: var(--white);
    --border: var(--border-dark);
  }
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, "Segoe UI", Inter, sans-serif;
  background: var(--bg);
  color: var(--text);
}
```

- [ ] **Step 6: Create `frontend/src/main.tsx`**

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 7: Install and verify**

Run:
```bash
cd frontend && npm install
npm run dev -- --port 5173 &
sleep 3 && curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
kill %1
```
Expected: `200` (App.tsx doesn't exist yet, so this will actually fail to
compile — that's fine, verified fully in Task 8 once App.tsx exists;
this step just confirms `npm install` and `vite` itself work).

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src/styles/tokens.css frontend/src/main.tsx
git commit -m "chore: scaffold frontend project with design tokens"
```

---

## Task 8: Frontend — VerdictBadge + RankedTable + App

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/VerdictBadge.tsx`
- Create: `frontend/src/components/RankedTable.tsx`
- Create: `frontend/src/App.tsx`
- Test: `frontend/src/components/RankedTable.test.tsx`

- [ ] **Step 1: Write the failing test** — `frontend/src/components/RankedTable.test.tsx`

```typescript
import { render, screen } from "@testing-library/react";
import { RankedTable, type StockSummary } from "./RankedTable";

const stocks: StockSummary[] = [
  {
    ticker: "RELIANCE.NS",
    name: "Reliance Industries",
    long_term_label: "Buy",
    short_term_label: "Hold",
    long_term_score: 78.4,
    short_term_score: 55.0,
    computed_at: "2026-08-31T18:00:00Z",
    excluded_reason: null,
  },
];

test("renders a row per stock with its long-term verdict label", () => {
  render(<RankedTable stocks={stocks} />);
  expect(screen.getByText("RELIANCE.NS")).toBeInTheDocument();
  expect(screen.getByText("Buy")).toBeInTheDocument();
});

test("renders excluded reason instead of a score when present", () => {
  const excluded: StockSummary[] = [
    { ...stocks[0], long_term_label: null, excluded_reason: "not yet scored" },
  ];
  render(<RankedTable stocks={excluded} />);
  expect(screen.getByText("not yet scored")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/RankedTable.test.tsx`
Expected: FAIL — cannot find module `./RankedTable`

- [ ] **Step 3: Create `frontend/src/api/client.ts`**

```typescript
export interface StockSummary {
  ticker: string;
  name: string;
  long_term_label: string | null;
  short_term_label: string | null;
  long_term_score: number | null;
  short_term_score: number | null;
  computed_at: string | null;
  excluded_reason: string | null;
}

const API_BASE = "http://localhost:8000";

export async function fetchStocks(): Promise<StockSummary[]> {
  const response = await fetch(`${API_BASE}/stocks`);
  if (!response.ok) {
    throw new Error(`failed to fetch stocks: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 4: Create `frontend/src/components/VerdictBadge.tsx`**

```typescript
const LABEL_COLOR: Record<string, string> = {
  "Strong Buy": "var(--signal-strong-buy)",
  Buy: "var(--signal-buy)",
  Hold: "var(--signal-hold)",
  Avoid: "var(--signal-avoid)",
};

export function VerdictBadge({ label }: { label: string }) {
  const color = LABEL_COLOR[label] ?? "var(--ink-400)";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 600,
        color,
        backgroundColor: `${color}26`,
        border: `1px solid ${color}`,
      }}
    >
      {label}
    </span>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/RankedTable.tsx`**

```typescript
import { VerdictBadge } from "./VerdictBadge";
import type { StockSummary } from "../api/client";

export type { StockSummary } from "../api/client";

export function RankedTable({ stocks }: { stocks: StockSummary[] }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ background: "var(--lavender-100)", textAlign: "left" }}>
          <th style={{ padding: "8px 12px" }}>Ticker</th>
          <th style={{ padding: "8px 12px" }}>Name</th>
          <th style={{ padding: "8px 12px" }}>Long-Term</th>
          <th style={{ padding: "8px 12px" }}>Short-Term</th>
        </tr>
      </thead>
      <tbody>
        {stocks.map((stock) => (
          <tr key={stock.ticker} style={{ borderBottom: "1px solid var(--border)" }}>
            <td style={{ padding: "8px 12px" }}>{stock.ticker}</td>
            <td style={{ padding: "8px 12px" }}>{stock.name}</td>
            <td style={{ padding: "8px 12px" }}>
              {stock.long_term_label ? (
                <VerdictBadge label={stock.long_term_label} />
              ) : (
                <span style={{ color: "var(--ink-400)" }}>{stock.excluded_reason}</span>
              )}
            </td>
            <td style={{ padding: "8px 12px" }}>
              {stock.short_term_label ? (
                <VerdictBadge label={stock.short_term_label} />
              ) : (
                <span style={{ color: "var(--ink-400)" }}>{stock.excluded_reason}</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/RankedTable.test.tsx`
Expected: 2 passed

- [ ] **Step 7: Create `frontend/src/App.tsx`**

```typescript
import { useEffect, useState } from "react";
import { fetchStocks, type StockSummary } from "./api/client";
import { RankedTable } from "./components/RankedTable";

export function App() {
  const [stocks, setStocks] = useState<StockSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStocks()
      .then(setStocks)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px" }}>
      <h1 style={{ color: "var(--lavender-700)" }}>Fintrixa</h1>
      {error && <p style={{ color: "var(--signal-avoid)" }}>{error}</p>}
      {!error && !stocks && <p>Loading…</p>}
      {stocks && <RankedTable stocks={stocks} />}
    </main>
  );
}
```

- [ ] **Step 8: Manual verification**

Run:
```bash
cd backend && source .venv/bin/activate && uvicorn app.api.main:app --reload &
cd frontend && npm run dev &
```
Open `http://localhost:5173` in a browser. Expected: page renders
"Fintrixa" heading in lavender, and either a ranked table row or an error
message (no seeded stocks yet is fine — that's Task 9). Kill both
background processes when done.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api/ frontend/src/components/ frontend/src/App.tsx
git commit -m "feat: render ranked table with verdict badges on dashboard"
```

---

## Task 9: Wire it together — seed one real ticker end to end

**Files:**
- Create: `backend/scripts/seed_one_ticker.py`

- [ ] **Step 1: Create `backend/scripts/seed_one_ticker.py`**

```python
"""Fetch RELIANCE.NS, score it, persist it — proves the full pipeline."""
from datetime import datetime

import pandas as pd

from app.db import SessionLocal
from app.ingestion.yfinance_client import fetch_fundamentals, fetch_price_history
from app.models import Score, Stock
from app.scoring.fundamental import compute_fundamental_score
from app.scoring.technical import compute_technical_score
from app.scoring.verdict import combine_scores

TICKER = "RELIANCE.NS"


def main():
    db = SessionLocal()

    stock = db.query(Stock).filter_by(ticker=TICKER).one_or_none()
    if stock is None:
        stock = Stock(ticker=TICKER, name="Reliance Industries")
        db.add(stock)
        db.flush()

    history = fetch_price_history(TICKER)
    closes = pd.Series(history["Close"].values)
    volumes = pd.Series(history["Volume"].values)

    technical = compute_technical_score(closes, volumes)
    fundamentals = fetch_fundamentals(TICKER)
    fundamental = compute_fundamental_score(fundamentals)
    combined = combine_scores(fundamental["score"], technical["score"])

    excluded_reason = (
        fundamental["excluded_reason"] or technical["excluded_reason"] or combined["excluded_reason"]
    )

    db.add(
        Score(
            stock_id=stock.id,
            computed_at=datetime.utcnow(),
            fundamental_score=fundamental["score"],
            technical_score=technical["score"],
            long_term_score=combined["long_term_score"],
            short_term_score=combined["short_term_score"],
            long_term_label=combined["long_term_label"],
            short_term_label=combined["short_term_label"],
            explanation=combined["explanation"],
            excluded_reason=excluded_reason,
        )
    )
    db.commit()
    print(f"scored {TICKER}: long_term={combined['long_term_label']}, short_term={combined['short_term_label']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run:
```bash
cd backend && source .venv/bin/activate
python scripts/seed_one_ticker.py
```
Expected: prints a `long_term=`/`short_term=` line — either real labels,
or the explicit `excluded_reason` if yfinance data was thin (a legitimate
outcome, not a bug — confirms the exclusion rule works against live data).

- [ ] **Step 3: Verify end to end in the browser**

Restart backend + frontend dev servers (Task 8, Step 8) and reload
`http://localhost:5173`. Expected: one row, RELIANCE.NS, with either a
verdict badge or an excluded-reason message — never a blank/undefined
cell.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/seed_one_ticker.py
git commit -m "feat: add end-to-end seed script proving the full pipeline"
```

---

## Next (separate plans, one per module, run in parallel once this merges)

Each below is its own `docs/superpowers/plans/` document, written just
before it's dispatched to its owning agent (see the module's `.claude/agents/*.md`) —
not written speculatively now, since each depends on the interfaces this
skeleton just locked in:

- **Ingestion breadth** (`data-ingestion-agent`): multi-ticker universe,
  screener.in fallback for fields yfinance lacks (sector P/E, ROCE,
  growth CAGR, promoter holding, pledge %), corporate actions feed,
  nightly/weekly scheduling.
- **Scoring breadth** (`scoring-engine-agent`): remaining components
  (growth, promoter holding, volume, MACD) once their data lands from
  ingestion breadth — raises the 55/65-point interim scales in Tasks 3-4
  to the full 100/100 the skill defines.
- **Backtest** (`backtest-agent`): full replay engine + release gate per
  `.claude/skills/fintrixa-backtest-methodology` — needs multi-ticker,
  multi-window history from ingestion breadth first.
- **News/LLM layer** (`news-llm-agent`): shortlist corroboration per
  `.claude/skills/fintrixa-scoring-formula`'s red-flag override rule.
- **API breadth** (`api-agent`): filters (sector/market-cap/verdict),
  stale-data freshness field, price-history payload for charts.
- **Frontend breadth** (`frontend-agent`): filters UI, stock detail page,
  price chart, stale-data banner, dark-mode polish, accessibility pass.
- **QA pass** (`qa-agent`): run after each breadth plan lands.
