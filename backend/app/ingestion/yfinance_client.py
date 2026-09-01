from datetime import date

import pandas as pd
import yfinance as yf

from app.models import DailyPrice


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
        "sector": info.get("sector"),  # GICS-style sector string, used for peer-group sector_pe
        "trailing_pe": info.get("trailingPE"),
        "sector_pe": None,  # filled in by enrich_sector_pe() across the fetched universe
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


def persist_price_history(db, stock_id: int, rows: list[dict]) -> int:
    """Upsert normalized price rows (from `normalize_price_history`) into
    the `daily_prices` table, keyed on (stock_id, trade_date). Skips rows
    whose (stock_id, trade_date) already exist so re-running ingestion for
    an overlapping date range never produces duplicate rows. Does not
    commit — caller controls the transaction. Returns the number of rows
    actually inserted."""
    if not rows:
        return 0

    existing_dates = {
        d
        for (d,) in db.query(DailyPrice.trade_date)
        .filter(DailyPrice.stock_id == stock_id)
        .all()
    }

    inserted = 0
    for row in rows:
        trade_date = date.fromisoformat(row["trade_date"])
        if trade_date in existing_dates:
            continue
        db.add(
            DailyPrice(
                stock_id=stock_id,
                trade_date=trade_date,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
        )
        existing_dates.add(trade_date)
        inserted += 1
    return inserted
