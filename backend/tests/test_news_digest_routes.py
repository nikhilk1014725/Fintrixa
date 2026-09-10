from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.db import Base, get_db
from app.models import NewsCorroboration, Stock


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
    stock_a = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    stock_b = Stock(ticker="RELIANCE.NS", name="Reliance Industries")
    stock_c = Stock(ticker="INFY.NS", name="Infosys")
    db.add_all([stock_a, stock_b, stock_c])
    db.flush()

    db.add(
        NewsCorroboration(
            stock_id=stock_a.id,
            computed_at=datetime(2026, 9, 9, 8, 0, 0),
            bull_case="bull",
            bear_case="bear",
            red_flags=["old flag"],
            confidence="Mixed",
            sources=[],
        )
    )
    db.add(
        NewsCorroboration(
            stock_id=stock_a.id,
            computed_at=datetime(2026, 9, 10, 8, 0, 0),
            bull_case="bull",
            bear_case="bear",
            red_flags=[],
            confidence="Corroborated",
            sources=[],
        )
    )
    db.add(
        NewsCorroboration(
            stock_id=stock_b.id,
            computed_at=datetime(2026, 9, 10, 8, 5, 0),
            bull_case="bull",
            bear_case="bear",
            red_flags=["flag one", "flag two"],
            confidence="Mixed",
            sources=[],
        )
    )
    # stock_c has no NewsCorroboration row at all -- must not appear
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


def test_news_digest_returns_rows_sorted_by_computed_at_desc(client):
    response = client.get("/news-digest")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    tickers_in_order = [row["ticker"] for row in body]
    assert tickers_in_order == ["RELIANCE.NS", "TCS.NS", "TCS.NS"]


def test_news_digest_includes_red_flag_count(client):
    response = client.get("/news-digest")
    body = response.json()
    reliance_row = next(r for r in body if r["ticker"] == "RELIANCE.NS")
    assert reliance_row["red_flag_count"] == 2
    assert reliance_row["confidence"] == "Mixed"


def test_news_digest_zero_red_flags_returns_zero_count(client):
    response = client.get("/news-digest")
    body = response.json()
    latest_tcs_row = next(
        r for r in body if r["ticker"] == "TCS.NS" and r["computed_at"].startswith("2026-09-10")
    )
    assert latest_tcs_row["red_flag_count"] == 0


def test_news_digest_excludes_stocks_with_no_corroboration(client):
    response = client.get("/news-digest")
    body = response.json()
    tickers = {row["ticker"] for row in body}
    assert "INFY.NS" not in tickers
