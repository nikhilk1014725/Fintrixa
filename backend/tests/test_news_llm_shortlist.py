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


def test_select_shortlist_breaks_ties_deterministically_by_ticker(db_session):
    _add_scored_stock(db_session, "ZEBRA.NS", 80.0)
    _add_scored_stock(db_session, "ALPHA.NS", 80.0)
    _add_scored_stock(db_session, "MIDDLE.NS", 80.0)

    shortlist = select_shortlist(db_session, top_n=2)

    # all three tie on score -- deterministic tiebreak must pick the two
    # alphabetically-first tickers, not depend on DB row order
    assert [s["ticker"] for s in shortlist] == ["ALPHA.NS", "MIDDLE.NS"]
