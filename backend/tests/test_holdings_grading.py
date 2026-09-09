from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import DailyPrice, Holding, Score, Stock
from app.scoring.holdings_grading import grade_holding


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_stock(db, ticker="RELIANCE.NS"):
    stock = Stock(ticker=ticker, name="Reliance Industries")
    db.add(stock)
    db.flush()
    return stock


def test_tracking_as_expected_when_bullish_call_and_price_up(db):
    stock = _make_stock(db)
    db.add(
        Score(
            stock_id=stock.id,
            computed_at=datetime(2026, 1, 1),
            long_term_label="Strong Buy",
            short_term_label="Hold",
        )
    )
    db.add(
        DailyPrice(
            stock_id=stock.id,
            trade_date=date(2026, 3, 1),
            open=100,
            high=110,
            low=95,
            close=120,
            volume=1000,
        )
    )
    db.flush()

    holding = Holding(
        stock_id=stock.id,
        buy_price=100.0,
        quantity=10,
        buy_date=date(2026, 2, 1),
        created_at=datetime(2026, 2, 1),
    )
    db.add(holding)
    db.flush()

    result = grade_holding(db, holding)

    assert result["verdict_in_effect"] == "Strong Buy"
    assert result["tracking_status"] == "tracking_as_expected"
    assert result["current_price"] == 120
    assert result["gain_loss_pct"] == 20.0
    assert result["gain_loss_abs"] == 200.0


def test_not_tracking_as_expected_when_bullish_call_and_price_down(db):
    stock = _make_stock(db)
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
            trade_date=date(2026, 3, 1),
            open=100,
            high=100,
            low=80,
            close=80,
            volume=1000,
        )
    )
    db.flush()

    holding = Holding(
        stock_id=stock.id,
        buy_price=100.0,
        quantity=5,
        buy_date=date(2026, 2, 1),
        created_at=datetime(2026, 2, 1),
    )
    db.add(holding)
    db.flush()

    result = grade_holding(db, holding)

    assert result["verdict_in_effect"] == "Buy"
    assert result["tracking_status"] == "not_tracking_as_expected"
    assert result["gain_loss_pct"] == -20.0
    assert result["gain_loss_abs"] == -100.0


def test_no_bullish_call_when_verdict_is_hold(db):
    stock = _make_stock(db)
    db.add(
        Score(
            stock_id=stock.id,
            computed_at=datetime(2026, 1, 1),
            long_term_label="Hold",
            short_term_label="Avoid",
        )
    )
    db.add(
        DailyPrice(
            stock_id=stock.id,
            trade_date=date(2026, 3, 1),
            open=100,
            high=100,
            low=90,
            close=95,
            volume=1000,
        )
    )
    db.flush()

    holding = Holding(
        stock_id=stock.id,
        buy_price=100.0,
        quantity=1,
        buy_date=date(2026, 2, 1),
        created_at=datetime(2026, 2, 1),
    )
    db.add(holding)
    db.flush()

    result = grade_holding(db, holding)

    assert result["tracking_status"] == "no_bullish_call"
    assert result["verdict_in_effect"] == "Hold"


def test_no_call_on_record_when_no_score_before_buy_date(db):
    stock = _make_stock(db)
    db.add(
        Score(
            stock_id=stock.id,
            computed_at=datetime(2026, 5, 1),
            long_term_label="Buy",
            short_term_label="Buy",
        )
    )
    db.add(
        DailyPrice(
            stock_id=stock.id,
            trade_date=date(2026, 2, 5),
            open=100,
            high=100,
            low=100,
            close=100,
            volume=1000,
        )
    )
    db.flush()

    holding = Holding(
        stock_id=stock.id,
        buy_price=90.0,
        quantity=1,
        buy_date=date(2026, 2, 1),
        created_at=datetime(2026, 2, 1),
    )
    db.add(holding)
    db.flush()

    result = grade_holding(db, holding)

    assert result["tracking_status"] == "no_call_on_record"
    assert result["verdict_in_effect"] is None


def test_stale_price_surfaces_its_own_date(db):
    stock = _make_stock(db)
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
            trade_date=date(2026, 2, 20),
            open=100,
            high=100,
            low=100,
            close=110,
            volume=1000,
        )
    )
    db.flush()

    holding = Holding(
        stock_id=stock.id,
        buy_price=100.0,
        quantity=1,
        buy_date=date(2026, 2, 1),
        created_at=datetime(2026, 2, 1),
    )
    db.add(holding)
    db.flush()

    result = grade_holding(db, holding)

    assert result["price_as_of_date"] == date(2026, 2, 20)


def test_quantity_only_scales_absolute_gain_not_percentage(db):
    stock = _make_stock(db)
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
            trade_date=date(2026, 3, 1),
            open=100,
            high=100,
            low=100,
            close=110,
            volume=1000,
        )
    )
    db.flush()

    holding = Holding(
        stock_id=stock.id,
        buy_price=100.0,
        quantity=50,
        buy_date=date(2026, 2, 1),
        created_at=datetime(2026, 2, 1),
    )
    db.add(holding)
    db.flush()

    result = grade_holding(db, holding)

    assert result["gain_loss_pct"] == 10.0
    assert result["gain_loss_abs"] == 500.0
