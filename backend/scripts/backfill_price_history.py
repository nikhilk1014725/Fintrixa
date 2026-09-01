"""One-off backfill: fetches maximum available price history (yfinance
period='max') for every stock already in the DB and persists it.

The regular seed run only fetches 2y (enough for live scoring), but the
backtest methodology needs as much history as free data provides per
ticker for a meaningful number of rolling windows -- see
.claude/skills/fintrixa-backtest-methodology and
docs/superpowers/specs/2026-09-01-backtest-foundation-design.md."""
import time

from app.db import SessionLocal
from app.ingestion.yfinance_client import (
    fetch_price_history,
    normalize_price_history,
    persist_price_history,
)
from app.models import Stock

RATE_LIMIT_DELAY_SECONDS = 0.5


def main():
    db = SessionLocal()
    stocks = db.query(Stock).all()
    print(f"backfilling max price history for {len(stocks)} stocks")

    for stock in stocks:
        history = fetch_price_history(stock.ticker, period="max")
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

        rows = normalize_price_history(history)
        inserted = persist_price_history(db, stock.id, rows)
        db.commit()

        print(f"{stock.ticker}: {len(rows)} rows fetched, {inserted} new rows inserted")


if __name__ == "__main__":
    main()
