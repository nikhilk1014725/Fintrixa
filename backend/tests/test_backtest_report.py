from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backtest.report import run_backtest
from app.db import Base
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


def _seed_stock_with_history(db, ticker, n_days, start=date(2020, 1, 1), seed=0):
    stock = Stock(ticker=ticker, name=ticker)
    db.add(stock)
    db.flush()

    price = 100.0
    for i in range(n_days):
        price += ((i * 7 + seed * 13) % 11) - 5  # deterministic pseudo-movement
        price = max(price, 1.0)
        db.add(
            DailyPrice(
                stock_id=stock.id,
                trade_date=start + timedelta(days=i),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000.0 + (i % 50),
            )
        )
    db.commit()
    return stock


def test_run_backtest_reports_insufficient_history_when_too_shallow(db_session):
    _seed_stock_with_history(db_session, "AAA.NS", n_days=100)
    _seed_stock_with_history(db_session, "BBB.NS", n_days=100, seed=1)

    report = run_backtest(db_session, horizon_trading_days=21, horizon_label="T+1mo")

    assert report["status"] == "insufficient history"


def test_run_backtest_produces_well_formed_report_with_enough_history(db_session):
    n_days = 200 + 8 * 63 + 63 + 10  # min_history + 8 windows + horizon room + buffer
    for i, ticker in enumerate(["AAA.NS", "BBB.NS", "CCC.NS", "DDD.NS", "EEE.NS", "FFF.NS"]):
        _seed_stock_with_history(db_session, ticker, n_days=n_days, seed=i)

    report = run_backtest(db_session, horizon_trading_days=21, horizon_label="T+1mo")

    assert report["status"] in ("pass", "fail")
    assert report["usable_windows"] >= 8
    assert report["horizon"] == "T+1mo"
    assert "top_quartile_pass_rate" in report
    assert "bottom_quartile_pass_rate" in report
    assert len(report["windows"]) >= 8


def _fake_window_result(top_beats_median, bottom_at_or_below_median):
    """Returns a minimal valid window result dict for mocking evaluate_window."""
    return {
        "usable": True,
        "n_participants": 4,
        "quartile_size": 1,
        "median_return": 0.0,
        "top_quartile_mean": 0.01,
        "bottom_quartile_mean": -0.01,
        "top_beats_median": top_beats_median,
        "bottom_at_or_below_median": bottom_at_or_below_median,
    }


def test_run_backtest_passes_when_both_conditions_met_every_window(db_session):
    n_days = 200 + 8 * 63 + 63 + 10
    for i, ticker in enumerate(["AAA.NS", "BBB.NS", "CCC.NS", "DDD.NS"]):
        _seed_stock_with_history(db_session, ticker, n_days=n_days, seed=i)

    with patch(
        "app.backtest.report.evaluate_window",
        return_value=_fake_window_result(top_beats_median=True, bottom_at_or_below_median=True),
    ):
        report = run_backtest(db_session, horizon_trading_days=21, horizon_label="T+1mo")

    assert report["status"] == "pass"
    assert report["top_quartile_pass_rate"] == 1.0
    assert report["bottom_quartile_pass_rate"] == 1.0


def test_run_backtest_fails_when_bottom_condition_never_met(db_session):
    n_days = 200 + 8 * 63 + 63 + 10
    for i, ticker in enumerate(["AAA.NS", "BBB.NS", "CCC.NS", "DDD.NS"]):
        _seed_stock_with_history(db_session, ticker, n_days=n_days, seed=i)

    with patch(
        "app.backtest.report.evaluate_window",
        return_value=_fake_window_result(top_beats_median=True, bottom_at_or_below_median=False),
    ):
        report = run_backtest(db_session, horizon_trading_days=21, horizon_label="T+1mo")

    assert report["status"] == "fail"
    assert report["top_quartile_pass_rate"] == 1.0
    assert report["bottom_quartile_pass_rate"] == 0.0
