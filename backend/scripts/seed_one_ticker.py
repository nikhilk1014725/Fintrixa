"""Fetch RELIANCE.NS, score it, persist it — proves the full pipeline."""
from datetime import datetime

import pandas as pd

from app.db import SessionLocal
from app.ingestion.yfinance_client import fetch_fundamentals, fetch_price_history
from app.models import Score, Stock
from app.scoring.fundamental import compute_fundamental_score
from app.scoring.technical import compute_technical_score
from app.scoring.verdict import combine_scores

TICKER = "RELIANCE.NS"


def main():
    db = SessionLocal()

    stock = db.query(Stock).filter_by(ticker=TICKER).one_or_none()
    if stock is None:
        stock = Stock(ticker=TICKER, name="Reliance Industries")
        db.add(stock)
        db.flush()

    history = fetch_price_history(TICKER)
    closes = pd.Series(history["Close"].values)
    volumes = pd.Series(history["Volume"].values)

    technical = compute_technical_score(closes, volumes)
    fundamentals = fetch_fundamentals(TICKER)
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
        print(f"scored {TICKER}: excluded_reason={excluded_reason}")
    else:
        print(f"scored {TICKER}: long_term={combined['long_term_label']}, short_term={combined['short_term_label']}")


if __name__ == "__main__":
    main()
