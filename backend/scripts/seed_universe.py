"""Fetch a starter universe of NSE large-caps, score them, persist them.

Supersedes seed_one_ticker.py: seeds enough tickers spanning multiple
sectors that sector_pe (peer-group average trailing PE, see
app.ingestion.enrichment.enrich_sector_pe) has at least 2 members per
sector to average over, instead of the field being permanently null.
"""
import time
from datetime import datetime

import pandas as pd

from app.db import SessionLocal
from app.ingestion.enrichment import enrich_sector_pe
from app.ingestion.yfinance_client import (
    fetch_fundamentals,
    fetch_price_history,
    normalize_price_history,
    persist_price_history,
)
from app.models import Score, Stock
from app.scoring.fundamental import compute_fundamental_score
from app.scoring.technical import compute_technical_score
from app.scoring.verdict import combine_scores

TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "WIPRO.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "KOTAKBANK.NS",
    "SBIN.NS",
    "ITC.NS",
    "HINDUNILVR.NS",
    "MARUTI.NS",
    "TATAMOTORS.NS",
    "SUNPHARMA.NS",
    "DRREDDY.NS",
    "ASIANPAINT.NS",
    "BHARTIARTL.NS",
    "LT.NS",
]

RATE_LIMIT_DELAY_SECONDS = 0.5


def main():
    db = SessionLocal()

    # Fetch fundamentals for the whole batch first so enrich_sector_pe has
    # the full universe to group/average over before any scoring happens.
    fundamentals_by_ticker = {}
    for ticker in TICKERS:
        fundamentals_by_ticker[ticker] = fetch_fundamentals(ticker)
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

    fundamentals_by_ticker = enrich_sector_pe(fundamentals_by_ticker)

    for ticker in TICKERS:
        stock = db.query(Stock).filter_by(ticker=ticker).one_or_none()
        if stock is None:
            stock = Stock(ticker=ticker, name=ticker.split(".")[0].title())
            db.add(stock)
            db.flush()

        history = fetch_price_history(ticker)
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

        rows = normalize_price_history(history)
        persist_price_history(db, stock.id, rows)

        closes = pd.Series(history["Close"].values) if not history.empty else pd.Series(dtype=float)
        volumes = pd.Series(history["Volume"].values) if not history.empty else pd.Series(dtype=float)

        technical = compute_technical_score(closes, volumes)
        fundamentals = fundamentals_by_ticker[ticker]
        fundamental = compute_fundamental_score(fundamentals)
        combined = combine_scores(fundamental["score"], technical["score"])

        excluded_reason = (
            fundamental["excluded_reason"] or technical["excluded_reason"] or combined["excluded_reason"]
        )

        db.add(
            Score(
                stock_id=stock.id,
                computed_at=datetime.utcnow(),
                fundamental_score=fundamental["score"],
                technical_score=technical["score"],
                long_term_score=combined["long_term_score"],
                short_term_score=combined["short_term_score"],
                long_term_label=combined["long_term_label"],
                short_term_label=combined["short_term_label"],
                explanation=combined["explanation"],
                excluded_reason=excluded_reason,
            )
        )
        db.commit()

        if excluded_reason:
            print(f"scored {ticker}: excluded_reason={excluded_reason}")
        else:
            print(
                f"scored {ticker}: long_term={combined['long_term_label']}, "
                f"short_term={combined['short_term_label']}"
            )


if __name__ == "__main__":
    main()
