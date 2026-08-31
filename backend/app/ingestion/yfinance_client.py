import pandas as pd
import yfinance as yf


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
        "trailing_pe": info.get("trailingPE"),
        "sector_pe": None,  # not available from yfinance; breadth plan adds sector-avg calc
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
