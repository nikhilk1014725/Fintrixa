from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.db import Base, get_db
from app.models import DailyPrice, NewsCorroboration, Score, Stock


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

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
    db.add(
        DailyPrice(
            stock_id=stock.id,
            trade_date=date(2026, 8, 28),
            open=2900.0,
            high=2920.0,
            low=2890.0,
            close=2910.0,
            volume=1000000.0,
        )
    )
    db.add(
        DailyPrice(
            stock_id=stock.id,
            trade_date=date(2026, 8, 27),
            open=2880.0,
            high=2905.0,
            low=2870.0,
            close=2895.0,
            volume=900000.0,
        )
    )
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            db.rollback()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db.close()


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


def test_list_stocks_includes_explanation_matching_detail_endpoint(client):
    list_response = client.get("/stocks")
    detail_response = client.get("/stocks/RELIANCE.NS")
    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    list_body = list_response.json()
    detail_body = detail_response.json()
    assert list_body[0]["explanation"] == "Long-term: buy on fundamentals (82/100)..."
    assert list_body[0]["explanation"] == detail_body["explanation"]


def test_stock_detail_unknown_ticker_returns_404(client):
    response = client.get("/stocks/NOPE.NS")
    assert response.status_code == 404


def test_stock_history_returns_prices_ascending(client):
    response = client.get("/stocks/RELIANCE.NS/history")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["trade_date"] == "2026-08-27"
    assert body[1]["trade_date"] == "2026-08-28"
    assert body[0]["close"] == 2895.0
    assert set(body[0].keys()) == {"trade_date", "open", "high", "low", "close", "volume"}


def test_stock_history_unknown_ticker_returns_404(client):
    response = client.get("/stocks/NOPE.NS/history")
    assert response.status_code == 404
    assert response.json()["detail"] == "unknown ticker: NOPE.NS"


@pytest.fixture()
def client_with_red_flag():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    db = TestSession()
    stock = Stock(ticker="FLAGGED.NS", name="Flagged Corp")
    db.add(stock)
    db.flush()
    db.add(
        Score(
            stock_id=stock.id,
            computed_at=datetime(2026, 9, 1, 8, 0, 0),
            fundamental_score=82.0,
            technical_score=70.0,
            long_term_score=78.4,
            short_term_score=73.6,
            long_term_label="Strong Buy",
            short_term_label="Buy",
            explanation="test explanation",
            excluded_reason=None,
        )
    )
    db.add(
        NewsCorroboration(
            stock_id=stock.id,
            computed_at=datetime(2026, 9, 2, 8, 0, 0),
            bull_case="Strong order book.",
            bear_case="Margin pressure.",
            red_flags=["pending litigation over patent dispute"],
            confidence="Corroborated",
            sources=[{"title": "Filing", "url": "https://example.com/filing"}],
        )
    )
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            db.rollback()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db.close()


def test_stocks_list_shows_capped_label_when_active_red_flag(client_with_red_flag):
    response = client_with_red_flag.get("/stocks")
    assert response.status_code == 200
    body = response.json()
    flagged = next(s for s in body if s["ticker"] == "FLAGGED.NS")
    assert flagged["long_term_label"] == "Hold"
    assert flagged["short_term_label"] == "Hold"


def test_stock_detail_shows_news_fields_and_override_reason(client_with_red_flag):
    response = client_with_red_flag.get("/stocks/FLAGGED.NS")
    assert response.status_code == 200
    body = response.json()
    assert body["long_term_label"] == "Hold"
    assert body["short_term_label"] == "Hold"
    assert body["verdict_override_reason"] is not None
    assert "pending litigation over patent dispute" in body["verdict_override_reason"]
    assert body["news_confidence"] == "Corroborated"
    assert body["news_bull_case"] == "Strong order book."
    assert body["news_bear_case"] == "Margin pressure."
    assert body["news_red_flags"] == ["pending litigation over patent dispute"]
    assert body["news_researched_at"] is not None


def test_stock_detail_news_fields_null_when_never_researched(client):
    response = client.get("/stocks/RELIANCE.NS")
    assert response.status_code == 200
    body = response.json()
    assert body["news_confidence"] is None
    assert body["news_bull_case"] is None
    assert body["news_bear_case"] is None
    assert body["news_red_flags"] is None
    assert body["news_researched_at"] is None
    assert body["verdict_override_reason"] is None
    # no override applied -- raw score label unchanged
    assert body["long_term_label"] == "Buy"
