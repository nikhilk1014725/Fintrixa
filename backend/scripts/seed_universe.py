"""Fetch the live NIFTY 100 universe, score it, persist it.

Supersedes the old hardcoded 17-ticker starter list: pulls the current
NIFTY 100 constituents from NSE (see app.ingestion.nse_universe), uses
NSE's own Industry classification for sector_pe peer-grouping (see
app.ingestion.enrichment.enrich_sector_pe) instead of yfinance's sector
field.
"""
import time
from datetime import datetime

import pandas as pd

from app.db import SessionLocal
from app.ingestion.enrichment import enrich_sector_pe
from app.ingestion.nse_universe import fetch_nifty100_constituents
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

RATE_LIMIT_DELAY_SECONDS = 0.5


def main():
    db = SessionLocal()

    constituents = fetch_nifty100_constituents()
    print(f"fetched {len(constituents)} NIFTY 100 constituents from NSE")

    # Fetch fundamentals for the whole batch first so enrich_sector_pe has
    # the full universe to group/average over before any scoring happens.
    fundamentals_by_ticker = {}
    for c in constituents:
        fundamentals_by_ticker[c["ticker"]] = fetch_fundamentals(
            c["ticker"], sector_hint=c["sector"]
        )
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

    fundamentals_by_ticker = enrich_sector_pe(fundamentals_by_ticker)

    for c in constituents:
        ticker = c["ticker"]
        stock = db.query(Stock).filter_by(ticker=ticker).one_or_none()
        if stock is None:
            stock = Stock(ticker=ticker, name=c["name"])
            db.add(stock)
            db.flush()
        elif stock.name != c["name"]:
            stock.name = c["name"]

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
