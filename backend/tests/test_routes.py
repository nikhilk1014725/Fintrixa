from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.db import Base, get_db
from app.models import DailyPrice, Score, Stock


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
