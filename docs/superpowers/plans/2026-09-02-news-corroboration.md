# News Corroboration Layer Implementation Plan (Sub-project D)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data contract, persistence, and red-flag override logic for the news corroboration layer per `docs/superpowers/specs/2026-09-02-news-corroboration-design.md`, wire it into the API and frontend, then set up the actual daily Claude Code scheduled routine that performs the research.

**Architecture:** New `backend/app/news_llm/` module (shortlist selection, payload validation/persistence, red-flag override — no LLM API calls in Python), one new DB table + migration, two new scripts, API schema/route changes, frontend display changes, and a Claude Code cron routine set up last.

**Tech Stack:** Python/SQLAlchemy/Alembic (backend), React/TypeScript (frontend), Claude Code's `schedule` skill (the routine itself).

---

### Task 1: NewsCorroboration model + migration

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/alembic/versions/<generated>_add_news_corroborations.py`

- [ ] **Step 1: Add the model**

Add to `backend/app/models.py` — new imports `JSON, Text` from sqlalchemy, a `news_corroborations` relationship on `Stock`, and the new class:

```python
from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text
```

Add to the `Stock` class (alongside the existing `daily_prices`/`scores` relationships):
```python
    news_corroborations: Mapped[list["NewsCorroboration"]] = relationship(back_populates="stock")
```

Add a new class at the end of the file:
```python
class NewsCorroboration(Base):
    __tablename__ = "news_corroborations"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    bull_case: Mapped[str] = mapped_column(Text)
    bear_case: Mapped[str] = mapped_column(Text)
    red_flags: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[str] = mapped_column(String(20))
    sources: Mapped[list] = mapped_column(JSON)

    stock: Mapped["Stock"] = relationship(back_populates="news_corroborations")
```

- [ ] **Step 2: Generate and review the migration**

Run: `cd backend && .venv/bin/alembic revision --autogenerate -m "add news_corroborations table"`
Expected: a new file under `backend/alembic/versions/`. Open it and confirm it creates exactly the `news_corroborations` table with the columns above and the FK to `stocks.id` — Alembic's autogenerate can occasionally miss or misname things, verify by reading it, don't just trust the generated output blindly.

- [ ] **Step 3: Apply the migration**

Run: `cd backend && .venv/bin/alembic upgrade head`
Expected: succeeds against the local Postgres. Confirm with `.venv/bin/python -c "from app.db import engine; from sqlalchemy import inspect; print('news_corroborations' in inspect(engine).get_table_names())"` → `True`.

- [ ] **Step 4: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all existing tests still pass (model addition alone shouldn't break anything).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/alembic/versions/
git commit -m "feat: add NewsCorroboration model and migration"
```

---

### Task 2: shortlist selection

**Files:**
- Create: `backend/app/news_llm/__init__.py` (empty)
- Create: `backend/app/news_llm/shortlist.py`
- Test: `backend/tests/test_news_llm_shortlist.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Score, Stock
from app.news_llm.shortlist import select_shortlist


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def _add_scored_stock(db, ticker, long_term_score):
    stock = Stock(ticker=ticker, name=ticker)
    db.add(stock)
    db.flush()
    db.add(
        Score(
            stock_id=stock.id,
            computed_at=datetime.utcnow(),
            fundamental_score=70.0,
            technical_score=70.0,
            long_term_score=long_term_score,
            short_term_score=long_term_score,
            long_term_label="Buy",
            short_term_label="Buy",
            explanation="test",
            excluded_reason=None,
        )
    )
    db.commit()


def test_select_shortlist_returns_top_n_by_long_term_score(db_session):
    _add_scored_stock(db_session, "A.NS", 90.0)
    _add_scored_stock(db_session, "B.NS", 50.0)
    _add_scored_stock(db_session, "C.NS", 70.0)

    shortlist = select_shortlist(db_session, top_n=2)

    assert [s["ticker"] for s in shortlist] == ["A.NS", "C.NS"]


def test_select_shortlist_excludes_unscored_stocks(db_session):
    _add_scored_stock(db_session, "A.NS", 90.0)
    unscored = Stock(ticker="B.NS", name="B")
    db_session.add(unscored)
    db_session.commit()

    shortlist = select_shortlist(db_session, top_n=5)

    assert [s["ticker"] for s in shortlist] == ["A.NS"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_llm_shortlist.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.news_llm'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/news_llm/__init__.py`: empty file.

`backend/app/news_llm/shortlist.py`:
```python
"""Selects the top-N shortlist for daily news research -- the actual
cost-control enforcement point per CLAUDE.md's "LLM cost control: news_llm
only runs on the top-N shortlist, never the full universe" rule."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Score, Stock


def select_shortlist(db: Session, top_n: int) -> list[dict]:
    """Returns the top_n stocks by long_term_score (using each stock's
    most recent Score row), as [{"ticker": ..., "name": ...,
    "long_term_score": ...}], sorted descending. Stocks with no score or
    a null long_term_score are excluded -- there's nothing to shortlist
    for a stock that isn't scored."""
    stocks = db.execute(select(Stock)).scalars().all()
    scored = []
    for stock in stocks:
        stmt = (
            select(Score)
            .where(Score.stock_id == stock.id)
            .order_by(Score.computed_at.desc())
            .limit(1)
        )
        score = db.execute(stmt).scalar_one_or_none()
        if score is None or score.long_term_score is None:
            continue
        scored.append(
            {
                "ticker": stock.ticker,
                "name": stock.name,
                "long_term_score": score.long_term_score,
            }
        )
    scored.sort(key=lambda s: s["long_term_score"], reverse=True)
    return scored[:top_n]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_llm_shortlist.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/news_llm/__init__.py backend/app/news_llm/shortlist.py backend/tests/test_news_llm_shortlist.py
git commit -m "feat: add news_llm shortlist selection"
```

---

### Task 3: research payload validation + persistence

**Files:**
- Create: `backend/app/news_llm/ingest.py`
- Test: `backend/tests/test_news_llm_ingest.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import NewsCorroboration, Stock
from app.news_llm.ingest import ResearchPayloadError, validate_and_persist_research


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def _valid_payload(ticker="TCS.NS"):
    return {
        "ticker": ticker,
        "bull_case": "Strong order book, margin expansion.",
        "bear_case": "Client concentration risk in BFSI.",
        "red_flags": [],
        "confidence": "Corroborated",
        "sources": [{"title": "Q2 results", "url": "https://example.com/q2"}],
    }


def test_validate_and_persist_research_valid_payload(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    corroboration = validate_and_persist_research(db_session, _valid_payload())

    assert corroboration.stock_id == stock.id
    assert corroboration.confidence == "Corroborated"
    assert db_session.query(NewsCorroboration).count() == 1


def test_validate_and_persist_research_rejects_invalid_confidence(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    payload = _valid_payload()
    payload["confidence"] = "Very Sure"

    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, payload)


def test_validate_and_persist_research_rejects_unknown_ticker(db_session):
    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, _valid_payload(ticker="NOPE.NS"))


def test_validate_and_persist_research_rejects_missing_bull_or_bear_case(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    payload = _valid_payload()
    payload["bull_case"] = ""

    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_llm_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.news_llm.ingest'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/news_llm/ingest.py`:
```python
"""Validates and persists a research-result payload from the daily news
research routine. The LLM call itself happens outside this codebase (a
Claude Code scheduled routine, see
docs/superpowers/specs/2026-09-02-news-corroboration-design.md) -- this
module only owns the data contract and persistence."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NewsCorroboration, Stock

VALID_CONFIDENCE_TAGS = {"Corroborated", "Mixed", "Unconfirmed"}


class ResearchPayloadError(ValueError):
    """Raised when a research-result payload fails validation."""


def validate_and_persist_research(db: Session, payload: dict) -> NewsCorroboration:
    """payload: {"ticker": str, "bull_case": str, "bear_case": str,
    "red_flags": list[str], "confidence": str, "sources": list[{"title":
    str, "url": str}]}. Raises ResearchPayloadError on any invalid field
    -- never silently coerces or drops a bad payload. Does not commit --
    caller controls the transaction."""
    ticker = payload.get("ticker")
    if not ticker:
        raise ResearchPayloadError("payload missing 'ticker'")

    stock = db.execute(select(Stock).where(Stock.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        raise ResearchPayloadError(f"unknown ticker: {ticker}")

    confidence = payload.get("confidence")
    if confidence not in VALID_CONFIDENCE_TAGS:
        raise ResearchPayloadError(
            f"invalid confidence '{confidence}', must be one of {sorted(VALID_CONFIDENCE_TAGS)}"
        )

    bull_case = payload.get("bull_case")
    bear_case = payload.get("bear_case")
    if not bull_case or not bear_case:
        raise ResearchPayloadError("payload missing 'bull_case' or 'bear_case'")

    red_flags = payload.get("red_flags", [])
    if not isinstance(red_flags, list):
        raise ResearchPayloadError("'red_flags' must be a list")

    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ResearchPayloadError("'sources' must be a list")

    corroboration = NewsCorroboration(
        stock_id=stock.id,
        computed_at=datetime.utcnow(),
        bull_case=bull_case,
        bear_case=bear_case,
        red_flags=red_flags,
        confidence=confidence,
        sources=sources,
    )
    db.add(corroboration)
    db.flush()
    return corroboration
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_llm_ingest.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/news_llm/ingest.py backend/tests/test_news_llm_ingest.py
git commit -m "feat: add news_llm research-payload validation and persistence"
```

---

### Task 4: red-flag override logic

**Files:**
- Create: `backend/app/news_llm/override.py`
- Test: `backend/tests/test_news_llm_override.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime

from app.models import NewsCorroboration, Score
from app.news_llm.override import apply_red_flag_override


def _score(long_term_label="Strong Buy", short_term_label="Buy"):
    return Score(
        stock_id=1,
        computed_at=datetime.utcnow(),
        fundamental_score=80.0,
        technical_score=70.0,
        long_term_score=85.0,
        short_term_score=75.0,
        long_term_label=long_term_label,
        short_term_label=short_term_label,
        explanation="test",
        excluded_reason=None,
    )


def _corroboration(red_flags):
    return NewsCorroboration(
        stock_id=1,
        computed_at=datetime.utcnow(),
        bull_case="bull",
        bear_case="bear",
        red_flags=red_flags,
        confidence="Corroborated",
        sources=[],
    )


def test_no_corroboration_no_override():
    result = apply_red_flag_override(_score(), None)

    assert result["long_term_label"] == "Strong Buy"
    assert result["short_term_label"] == "Buy"
    assert result["override_reason"] is None


def test_empty_red_flags_no_override():
    result = apply_red_flag_override(_score(), _corroboration([]))

    assert result["long_term_label"] == "Strong Buy"
    assert result["override_reason"] is None


def test_active_red_flag_caps_strong_buy_and_buy_to_hold():
    result = apply_red_flag_override(
        _score(long_term_label="Strong Buy", short_term_label="Buy"),
        _corroboration(["pending litigation"]),
    )

    assert result["long_term_label"] == "Hold"
    assert result["short_term_label"] == "Hold"
    assert result["override_reason"] is not None
    assert "pending litigation" in result["override_reason"]


def test_active_red_flag_does_not_raise_hold_or_avoid():
    result = apply_red_flag_override(
        _score(long_term_label="Hold", short_term_label="Avoid"),
        _corroboration(["regulatory action"]),
    )

    assert result["long_term_label"] == "Hold"
    assert result["short_term_label"] == "Avoid"


def test_no_score_no_override():
    result = apply_red_flag_override(None, _corroboration(["litigation"]))

    assert result["long_term_label"] is None
    assert result["short_term_label"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_llm_override.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.news_llm.override'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/news_llm/override.py`:
```python
"""Applies the red-flag override: caps a stock's displayed verdict at
Hold when an active red flag is present in its latest news corroboration,
regardless of the numeric score -- per .claude/skills/fintrixa-scoring-
formula's "Red-flag override" section. Never raises a label, only caps it
down."""
from app.models import NewsCorroboration, Score

CAPPED_LABEL = "Hold"
LABELS_SUBJECT_TO_CAP = {"Strong Buy", "Buy"}


def apply_red_flag_override(score: Score | None, corroboration: NewsCorroboration | None) -> dict:
    """Returns {"long_term_label": ..., "short_term_label": ...,
    "override_reason": ...} -- the EFFECTIVE labels to display. If there's
    no active red flag (no corroboration, or corroboration with an empty
    red_flags list), returns the score's own labels unchanged and
    override_reason=None."""
    long_term_label = score.long_term_label if score else None
    short_term_label = score.short_term_label if score else None

    if corroboration is None or not corroboration.red_flags:
        return {
            "long_term_label": long_term_label,
            "short_term_label": short_term_label,
            "override_reason": None,
        }

    reason = f"Active red flag(s) found: {'; '.join(corroboration.red_flags)}"
    effective_long = CAPPED_LABEL if long_term_label in LABELS_SUBJECT_TO_CAP else long_term_label
    effective_short = CAPPED_LABEL if short_term_label in LABELS_SUBJECT_TO_CAP else short_term_label

    return {
        "long_term_label": effective_long,
        "short_term_label": effective_short,
        "override_reason": reason,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_llm_override.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/news_llm/override.py backend/tests/test_news_llm_override.py
git commit -m "feat: add red-flag verdict override logic"
```

---

### Task 5: wire into the API

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/test_routes.py`

**Context:** The override must apply to BOTH `/stocks` (list) and `/stocks/{ticker}` (detail) — a layman must never see an uncapped "Strong Opportunity" badge in the list while the detail page shows it capped to Hold with a red-flag reason. That inconsistency would be exactly the kind of misleading-a-layman gap this project's persona explicitly guards against. `StockSummary`'s labels get the override applied; only `StockDetail` gets the new `news_*`/`verdict_override_reason` fields.

- [ ] **Step 1: Write the failing tests**

First, read the existing `backend/tests/test_routes.py` in full to see its exact fixture/TestClient setup, then add tests matching that same pattern:

```python
# Add these tests, adapting the exact fixture/client setup from the
# existing tests in this file -- don't guess, copy the established pattern.

def test_stocks_list_shows_capped_label_when_active_red_flag(...):
    # Seed a stock with a Score labeled "Strong Buy" and a NewsCorroboration
    # with a non-empty red_flags list.
    # GET /stocks, find that ticker's entry, assert long_term_label == "Hold"
    # (not "Strong Buy").
    ...

def test_stock_detail_shows_news_fields_and_override_reason(...):
    # Same seeded stock as above. GET /stocks/{ticker}.
    # Assert: long_term_label == "Hold", verdict_override_reason is not
    # None and mentions the red flag, news_confidence/news_bull_case/
    # news_bear_case/news_red_flags/news_researched_at all populated.
    ...

def test_stock_detail_news_fields_null_when_never_researched(...):
    # A stock with a Score but no NewsCorroboration row at all.
    # GET /stocks/{ticker}. Assert every news_* field and
    # verdict_override_reason is None, and long_term_label is the RAW
    # score label (no override applied).
    ...
```

Write the actual test bodies yourself, following the exact DB-seeding and `TestClient` pattern already used elsewhere in `test_routes.py` — do not invent a different fixture style.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_routes.py -v`
Expected: FAIL — `StockDetail` has no `news_confidence` field yet, etc.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas.py`, extend `StockDetail`:

```python
class StockDetail(StockSummary):
    fundamental_score: float | None
    technical_score: float | None
    explanation: str | None
    news_confidence: str | None
    news_bull_case: str | None
    news_bear_case: str | None
    news_red_flags: list[str] | None
    news_researched_at: datetime | None
    verdict_override_reason: str | None
```

In `backend/app/api/routes.py`, add the corroboration lookup helper and wire the override into both routes. Replace the full contents of the file:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DailyPrice, NewsCorroboration, Score, Stock
from app.news_llm.override import apply_red_flag_override
from app.schemas import PriceHistoryPoint, StockDetail, StockSummary

router = APIRouter()


def _latest_score(db: Session, stock: Stock) -> Score | None:
    stmt = (
        select(Score)
        .where(Score.stock_id == stock.id)
        .order_by(Score.computed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _latest_corroboration(db: Session, stock: Stock) -> NewsCorroboration | None:
    stmt = (
        select(NewsCorroboration)
        .where(NewsCorroboration.stock_id == stock.id)
        .order_by(NewsCorroboration.computed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


@router.get("/stocks", response_model=list[StockSummary])
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.execute(select(Stock)).scalars().all()
    results = []
    for stock in stocks:
        score = _latest_score(db, stock)
        corroboration = _latest_corroboration(db, stock)
        override = apply_red_flag_override(score, corroboration)
        results.append(
            StockSummary(
                ticker=stock.ticker,
                name=stock.name,
                long_term_label=override["long_term_label"],
                short_term_label=override["short_term_label"],
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
    corroboration = _latest_corroboration(db, stock)
    override = apply_red_flag_override(score, corroboration)

    return StockDetail(
        ticker=stock.ticker,
        name=stock.name,
        long_term_label=override["long_term_label"],
        short_term_label=override["short_term_label"],
        long_term_score=score.long_term_score if score else None,
        short_term_score=score.short_term_score if score else None,
        fundamental_score=score.fundamental_score if score else None,
        technical_score=score.technical_score if score else None,
        computed_at=score.computed_at if score else None,
        explanation=score.explanation if score else None,
        excluded_reason=score.excluded_reason if score else "not yet scored",
        news_confidence=corroboration.confidence if corroboration else None,
        news_bull_case=corroboration.bull_case if corroboration else None,
        news_bear_case=corroboration.bear_case if corroboration else None,
        news_red_flags=corroboration.red_flags if corroboration else None,
        news_researched_at=corroboration.computed_at if corroboration else None,
        verdict_override_reason=override["override_reason"],
    )


@router.get("/stocks/{ticker}/history", response_model=list[PriceHistoryPoint])
def stock_history(ticker: str, db: Session = Depends(get_db)):
    stock = db.execute(select(Stock).where(Stock.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"unknown ticker: {ticker}")

    stmt = (
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id)
        .order_by(DailyPrice.trade_date.asc())
    )
    return db.execute(stmt).scalars().all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_routes.py -v`
Expected: PASS, including the 3 new tests plus all pre-existing ones.

- [ ] **Step 5: Run the full backend test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/api/routes.py backend/tests/test_routes.py
git commit -m "feat: apply red-flag override and expose news fields via the API"
```

---

### Task 6: shortlist and ingest scripts

**Files:**
- Create: `backend/scripts/get_shortlist.py`
- Create: `backend/scripts/apply_news_corroboration.py`

**Context:** No unit tests (manual/integration scripts, same convention as `seed_universe.py`) — verified by actually running them in Task 8's dry run.

- [ ] **Step 1: Write `backend/scripts/get_shortlist.py`**

```python
"""Prints today's news-research shortlist as JSON. First step of the
daily Claude Code research routine -- see
docs/superpowers/specs/2026-09-02-news-corroboration-design.md."""
import json
import sys

from app.db import SessionLocal
from app.news_llm.shortlist import select_shortlist

TOP_N = 5


def main():
    db = SessionLocal()
    shortlist = select_shortlist(db, top_n=TOP_N)
    json.dump(shortlist, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `backend/scripts/apply_news_corroboration.py`**

```python
"""Reads a JSON array of research-result payloads and persists them.
Last step of the daily Claude Code research routine -- see
docs/superpowers/specs/2026-09-02-news-corroboration-design.md.

Usage: python scripts/apply_news_corroboration.py path/to/results.json
"""
import json
import sys

from app.db import SessionLocal
from app.news_llm.ingest import ResearchPayloadError, validate_and_persist_research


def main():
    if len(sys.argv) != 2:
        print("usage: apply_news_corroboration.py <results.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        payloads = json.load(f)

    db = SessionLocal()
    for payload in payloads:
        try:
            corroboration = validate_and_persist_research(db, payload)
            db.commit()
            print(f"{payload.get('ticker')}: persisted, confidence={corroboration.confidence}")
        except ResearchPayloadError as e:
            db.rollback()
            print(f"{payload.get('ticker', '?')}: REJECTED - {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke-test `get_shortlist.py` against the real DB**

Run: `cd backend && .venv/bin/python scripts/get_shortlist.py`
Expected: prints a JSON array of up to 5 `{ticker, name, long_term_score}` objects — the real currently-scored top stocks. Confirm the output is valid JSON and the tickers/scores look right against what you already know is in the DB.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/get_shortlist.py backend/scripts/apply_news_corroboration.py
git commit -m "feat: add shortlist and research-ingest CLI scripts"
```

---

### Task 7: frontend display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/StockDetail.tsx`
- Modify: `frontend/src/components/StockDetail.test.tsx`

- [ ] **Step 1: Extend the `StockDetail` type in `frontend/src/api/client.ts`**

```ts
export interface StockDetail extends StockSummary {
  fundamental_score: number | null;
  technical_score: number | null;
  explanation: string | null;
  news_confidence: string | null;
  news_bull_case: string | null;
  news_bear_case: string | null;
  news_red_flags: string[] | null;
  news_researched_at: string | null;
  verdict_override_reason: string | null;
}
```

- [ ] **Step 2: Write the failing tests**

Add to `frontend/src/components/StockDetail.test.tsx`. First update `baseDetail` to include the new fields (all `null`, since most existing tests describe a never-researched stock):

```tsx
const baseDetail: StockDetailData = {
  // ...existing fields unchanged...
  news_confidence: null,
  news_bull_case: null,
  news_bear_case: null,
  news_red_flags: null,
  news_researched_at: null,
  verdict_override_reason: null,
};
```

Then add:

```tsx
test("shows a red-flag warning card when active red flags are present", () => {
  const withRedFlag: StockDetailData = {
    ...baseDetail,
    news_confidence: "Corroborated",
    news_bull_case: "bull",
    news_bear_case: "bear",
    news_red_flags: ["pending litigation over patent dispute"],
    news_researched_at: "2026-09-02T08:00:00Z",
    verdict_override_reason: "Active red flag(s) found: pending litigation over patent dispute",
  };

  render(
    <StockDetail detail={withRedFlag} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />
  );

  expect(screen.getByText("⚠ Red flags found")).toBeInTheDocument();
  expect(screen.getByText(/pending litigation over patent dispute/)).toBeInTheDocument();
});

test("does not show a red-flag card when there are no red flags", () => {
  render(<StockDetail detail={baseDetail} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />);

  expect(screen.queryByText("⚠ Red flags found")).not.toBeInTheDocument();
});

test("shows bull/bear case and confidence in Show details when researched", async () => {
  const user = userEvent.setup();
  const researched: StockDetailData = {
    ...baseDetail,
    news_confidence: "Corroborated",
    news_bull_case: "Strong order book.",
    news_bear_case: "Client concentration risk.",
    news_red_flags: [],
    news_researched_at: "2026-09-02T08:00:00Z",
    verdict_override_reason: null,
  };

  render(<StockDetail detail={researched} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />);

  await user.click(screen.getByText("Show details"));

  expect(screen.getByText("Strong order book.")).toBeInTheDocument();
  expect(screen.getByText(/Corroborated/)).toBeInTheDocument();
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/StockDetail.test.tsx`
Expected: FAIL — no red-flag card, no news section exist yet.

- [ ] **Step 4: Write minimal implementation**

In `frontend/src/components/StockDetail.tsx`:

1. Add a red-flag warning card, rendered unconditionally (Level 1 — always visible, not behind "Show details"). Place it right after the "Suggested action" card:

```tsx
      {detail.news_red_flags && detail.news_red_flags.length > 0 && (
        <Card className="mb-6 border-signal-avoid/40 bg-signal-avoid/15">
          <CardHeader>
            <CardTitle className="text-base text-signal-avoid">⚠ Red flags found</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm text-ink-900 dark:text-white">
              {detail.news_red_flags.map((flag, i) => (
                <li key={i}>{flag}</li>
              ))}
            </ul>
            {detail.verdict_override_reason && (
              <p className="mt-3 text-xs text-ink-400">{detail.verdict_override_reason}</p>
            )}
          </CardContent>
        </Card>
      )}
```

2. Inside the existing `{showDetails && (...)}` block, after the "Score breakdown" `<Card>`, add a news-research card that only renders when the stock has actually been researched:

```tsx
      {showDetails && detail.news_researched_at && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">News research</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs uppercase tracking-wide text-ink-400">
              Confidence: {detail.news_confidence}
            </p>
            {detail.news_bull_case && (
              <div className="mt-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-ink-400">Bull case</div>
                <p className="text-sm text-ink-900 dark:text-white">{detail.news_bull_case}</p>
              </div>
            )}
            {detail.news_bear_case && (
              <div className="mt-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-ink-400">Bear case</div>
                <p className="text-sm text-ink-900 dark:text-white">{detail.news_bear_case}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
```

Note: this second block needs its own `{showDetails && ...}` conditional separate from the existing Score-breakdown block (don't merge them into one card — they're conceptually distinct: fundamentals/technicals vs. news research).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/StockDetail.test.tsx`
Expected: PASS (all tests, pre-existing + 3 new)

- [ ] **Step 6: Run the full frontend test suite**

Run: `cd frontend && npm test -- --run`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/components/StockDetail.tsx frontend/src/components/StockDetail.test.tsx
git commit -m "feat: display red flags and news research on the stock detail page"
```

---

### Task 8: set up the daily scheduled routine

**Files:** none (Claude Code configuration, not application code)

**Context:** This is set up using the `schedule` skill, not by writing application code. Do NOT attempt to hand-write a cron config file — invoke the skill.

- [ ] **Step 1: Manually dry-run the research flow once, end to end, before scheduling anything**

Run `cd backend && .venv/bin/python scripts/get_shortlist.py` to get today's real shortlist. For each ticker, use `WebSearch` to research recent news (~30 days), filings, analyst commentary. Produce bull case, bear case, red flags (litigation/fraud allegation/regulatory action ONLY — not routine negative news), and a confidence tag (`Corroborated` if multiple independent sources agree, `Mixed` if sources conflict, `Unconfirmed` if thin/single-source). Write the results as a JSON array matching the payload shape in Task 3, save to a file, then run `.venv/bin/python scripts/apply_news_corroboration.py <that file>`. Confirm it reports each ticker persisted successfully (not `REJECTED`). If any payload is rejected, fix the shape and retry — don't schedule a routine whose output the ingest script doesn't actually accept.

- [ ] **Step 2: Verify the result is visible end-to-end**

Hit `GET /stocks/{ticker}` for one of the researched tickers (backend dev server running) and confirm `news_confidence`/`news_bull_case`/`news_bear_case`/`news_researched_at` are populated, and — if you found any real red flag during the dry run — confirm the label is capped and `verdict_override_reason` is set. Load the frontend and visually confirm the red-flag card or the Show-details news section renders correctly.

- [ ] **Step 3: Set up the scheduled routine**

Invoke the `schedule` skill to create a daily cron routine. The routine's prompt should instruct a fresh session to: (1) run `get_shortlist.py`, (2) research each ticker via `WebSearch` per Step 1's criteria, (3) write results to a temp file and run `apply_news_corroboration.py` on it. Base the prompt on what actually worked in Step 1's manual dry run — don't write a substantially different prompt untested.

- [ ] **Step 4: Report the setup**

State plainly: the schedule's cadence/time, confirmation it was created (via whatever the `schedule` skill reports), and a reminder that its first real automated run should be checked (e.g. querying the DB for a fresh `NewsCorroboration.computed_at` after it fires) rather than assumed to have worked.
