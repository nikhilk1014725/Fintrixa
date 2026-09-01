import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.ingestion.enrichment import enrich_sector_pe
from app.ingestion.yfinance_client import normalize_price_history, persist_price_history
from app.models import DailyPrice, Stock


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


def test_enrich_sector_pe_computes_peer_group_mean():
    fundamentals = {
        "TCS.NS": {"sector": "Technology", "trailing_pe": 30.0},
        "INFY.NS": {"sector": "Technology", "trailing_pe": 20.0},
        "RELIANCE.NS": {"sector": "Energy", "trailing_pe": 25.0},
    }

    enriched = enrich_sector_pe(fundamentals)

    assert enriched["TCS.NS"]["sector_pe"] == 25.0
    assert enriched["INFY.NS"]["sector_pe"] == 25.0
    # only stock in its sector -> not a real peer comparison, stays None
    assert enriched["RELIANCE.NS"]["sector_pe"] is None


def test_enrich_sector_pe_skips_none_sector_and_none_trailing_pe():
    fundamentals = {
        "A": {"sector": None, "trailing_pe": 15.0},
        "B": {"sector": "Consumer", "trailing_pe": None},
        "C": {"sector": "Consumer", "trailing_pe": 18.0},
    }

    enriched = enrich_sector_pe(fundamentals)

    assert enriched["A"]["sector_pe"] is None
    # "Consumer" sector only has one usable trailing_pe (C's) -> below the
    # 2-member threshold, so neither B nor C get a fabricated sector_pe
    assert enriched["B"]["sector_pe"] is None
    assert enriched["C"]["sector_pe"] is None


def test_enrich_sector_pe_does_not_mutate_input():
    fundamentals = {
        "TCS.NS": {"sector": "Technology", "trailing_pe": 30.0},
        "INFY.NS": {"sector": "Technology", "trailing_pe": 20.0},
    }

    enrich_sector_pe(fundamentals)

    assert "sector_pe" not in fundamentals["TCS.NS"]
    assert "sector_pe" not in fundamentals["INFY.NS"]


def test_persist_price_history_inserts_rows(db_session):
    stock = Stock(ticker="RELIANCE.NS", name="Reliance Industries")
    db_session.add(stock)
    db_session.flush()

    rows = [
        {"trade_date": "2026-08-27", "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000.0},
        {"trade_date": "2026-08-28", "open": 104.0, "high": 106.0, "low": 103.0, "close": 105.0, "volume": 1100.0},
    ]

    inserted = persist_price_history(db_session, stock.id, rows)
    db_session.commit()

    assert inserted == 2
    assert db_session.query(DailyPrice).filter_by(stock_id=stock.id).count() == 2


def test_persist_price_history_skips_existing_trade_dates(db_session):
    stock = Stock(ticker="RELIANCE.NS", name="Reliance Industries")
    db_session.add(stock)
    db_session.flush()

    rows = [
        {"trade_date": "2026-08-27", "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000.0},
    ]
    persist_price_history(db_session, stock.id, rows)
    db_session.commit()

    # re-run ingestion for an overlapping range: same date plus one new one
    rows_rerun = [
        {"trade_date": "2026-08-27", "open": 999.0, "high": 999.0, "low": 999.0, "close": 999.0, "volume": 1.0},
        {"trade_date": "2026-08-28", "open": 104.0, "high": 106.0, "low": 103.0, "close": 105.0, "volume": 1100.0},
    ]
    inserted = persist_price_history(db_session, stock.id, rows_rerun)
    db_session.commit()

    assert inserted == 1
    prices = db_session.query(DailyPrice).filter_by(stock_id=stock.id).all()
    assert len(prices) == 2
    unchanged = next(p for p in prices if p.trade_date.isoformat() == "2026-08-27")
    assert unchanged.close == 104.0  # original row preserved, not overwritten with the "rerun" junk values


def test_persist_price_history_empty_rows_returns_zero(db_session):
    stock = Stock(ticker="RELIANCE.NS", name="Reliance Industries")
    db_session.add(stock)
    db_session.flush()

    assert persist_price_history(db_session, stock.id, []) == 0
