from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Score, Stock
from app.schemas import StockDetail, StockSummary

router = APIRouter()


def _latest_score(db: Session, stock: Stock) -> Score | None:
    stmt = (
        select(Score)
        .where(Score.stock_id == stock.id)
        .order_by(Score.computed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


@router.get("/stocks", response_model=list[StockSummary])
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.execute(select(Stock)).scalars().all()
    results = []
    for stock in stocks:
        score = _latest_score(db, stock)
        results.append(
            StockSummary(
                ticker=stock.ticker,
                name=stock.name,
                long_term_label=score.long_term_label if score else None,
                short_term_label=score.short_term_label if score else None,
                long_term_score=score.long_term_score if score else None,
                short_term_score=score.short_term_score if score else None,
                computed_at=score.computed_at if score else None,
                excluded_reason=score.excluded_reason if score else "not yet scored",
            )
        )
    return results


@router.get("/stocks/{ticker}", response_model=StockDetail)
def stock_detail(ticker: str, db: Session = Depends(get_db)):
    stock = db.execute(select(Stock).where(Stock.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"unknown ticker: {ticker}")

    score = _latest_score(db, stock)
    return StockDetail(
        ticker=stock.ticker,
        name=stock.name,
        long_term_label=score.long_term_label if score else None,
        short_term_label=score.short_term_label if score else None,
        long_term_score=score.long_term_score if score else None,
        short_term_score=score.short_term_score if score else None,
        fundamental_score=score.fundamental_score if score else None,
        technical_score=score.technical_score if score else None,
        computed_at=score.computed_at if score else None,
        explanation=score.explanation if score else None,
        excluded_reason=score.excluded_reason if score else "not yet scored",
    )
