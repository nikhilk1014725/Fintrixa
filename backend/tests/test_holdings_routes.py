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
            computed_at=datetime(2026, 1, 1),
            long_term_label="Buy",
            short_term_label="Hold",
        )
    )
    db.add(
        DailyPrice(
            stock_id=stock.id,
            trade_date=date(2026, 1, 5),
            open=100,
            high=100,
            low=100,
            close=100,
            volume=1000,
        )
    )
    db.add(
        DailyPrice(
            stock_id=stock.id,
            trade_date=date(2026, 3, 1),
            open=100,
            high=100,
            low=100,
            close=115,
            volume=1000,
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


def test_create_holding_returns_grading(client):
    response = client.post(
        "/holdings",
        json={"ticker": "RELIANCE.NS", "buy_price": 100.0, "quantity": 10, "buy_date": "2026-02-01"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "RELIANCE.NS"
    assert body["name"] == "Reliance Industries"
    assert body["grading"]["verdict_in_effect"] == "Buy"
    assert body["grading"]["tracking_status"] == "tracking_as_expected"
    assert body["grading"]["current_price"] == 115.0
    assert body["grading"]["gain_loss_pct"] == 15.0


def test_create_holding_rejects_unknown_ticker(client):
    response = client.post(
        "/holdings",
        json={"ticker": "NOPE.NS", "buy_price": 100.0, "quantity": 10, "buy_date": "2026-02-01"},
    )
    assert response.status_code == 400
    assert "don't track this stock" in response.json()["detail"]


def test_create_holding_rejects_future_buy_date(client):
    response = client.post(
        "/holdings",
        json={"ticker": "RELIANCE.NS", "buy_price": 100.0, "quantity": 10, "buy_date": "2099-01-01"},
    )
    assert response.status_code == 400
    assert "future" in response.json()["detail"]


def test_create_holding_rejects_buy_date_before_earliest_price(client):
    response = client.post(
        "/holdings",
        json={"ticker": "RELIANCE.NS", "buy_price": 100.0, "quantity": 10, "buy_date": "2020-01-01"},
    )
    assert response.status_code == 400
    assert "earliest data" in response.json()["detail"]


def test_list_holdings_returns_computed_grading(client):
    client.post(
        "/holdings",
        json={"ticker": "RELIANCE.NS", "buy_price": 100.0, "quantity": 10, "buy_date": "2026-02-01"},
    )
    response = client.get("/holdings")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["grading"]["gain_loss_pct"] == 15.0
