from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DailyPrice, Holding, NewsCorroboration, Score, Stock
from app.news_llm.override import apply_red_flag_override
from app.schemas import HoldingCreate, HoldingGrading, HoldingResponse, PriceHistoryPoint, StockDetail, StockSummary
from app.scoring.holdings_grading import grade_holding

router = APIRouter()


def _latest_score(db: Session, stock: Stock) -> Score | None:
    stmt = (
        select(Score)
        .where(Score.stock_id == stock.id)
        .order_by(Score.computed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _latest_corroboration(db: Session, stock: Stock) -> NewsCorroboration | None:
    stmt = (
        select(NewsCorroboration)
        .where(NewsCorroboration.stock_id == stock.id)
        .order_by(NewsCorroboration.computed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


@router.get("/stocks", response_model=list[StockSummary])
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.execute(select(Stock)).scalars().all()
    results = []
    for stock in stocks:
        score = _latest_score(db, stock)
        corroboration = _latest_corroboration(db, stock)
        override = apply_red_flag_override(score, corroboration)
        results.append(
            StockSummary(
                ticker=stock.ticker,
                name=stock.name,
                long_term_label=override["long_term_label"],
                short_term_label=override["short_term_label"],
                long_term_score=score.long_term_score if score else None,
                short_term_score=score.short_term_score if score else None,
                computed_at=score.computed_at if score else None,
                explanation=score.explanation if score else None,
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
    corroboration = _latest_corroboration(db, stock)
    override = apply_red_flag_override(score, corroboration)

    return StockDetail(
        ticker=stock.ticker,
        name=stock.name,
        long_term_label=override["long_term_label"],
        short_term_label=override["short_term_label"],
        long_term_score=score.long_term_score if score else None,
        short_term_score=score.short_term_score if score else None,
        fundamental_score=score.fundamental_score if score else None,
        technical_score=score.technical_score if score else None,
        computed_at=score.computed_at if score else None,
        explanation=score.explanation if score else None,
        excluded_reason=score.excluded_reason if score else "not yet scored",
        news_confidence=corroboration.confidence if corroboration else None,
        news_bull_case=corroboration.bull_case if corroboration else None,
        news_bear_case=corroboration.bear_case if corroboration else None,
        news_red_flags=corroboration.red_flags if corroboration else None,
        news_researched_at=corroboration.computed_at if corroboration else None,
        verdict_override_reason=override["override_reason"],
    )


@router.get("/stocks/{ticker}/history", response_model=list[PriceHistoryPoint])
def stock_history(ticker: str, db: Session = Depends(get_db)):
    stock = db.execute(select(Stock).where(Stock.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"unknown ticker: {ticker}")

    stmt = (
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id)
        .order_by(DailyPrice.trade_date.asc())
    )
    return db.execute(stmt).scalars().all()


def _holding_response(db: Session, holding: Holding) -> HoldingResponse:
    grading = grade_holding(db, holding)
    return HoldingResponse(
        id=holding.id,
        ticker=holding.stock.ticker,
        name=holding.stock.name,
        buy_price=holding.buy_price,
        quantity=holding.quantity,
        buy_date=holding.buy_date,
        grading=HoldingGrading(**grading),
    )


@router.post("/holdings", response_model=HoldingResponse, status_code=201)
def create_holding(payload: HoldingCreate, db: Session = Depends(get_db)):
    stock = db.execute(select(Stock).where(Stock.ticker == payload.ticker)).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=400, detail=f"we don't track this stock yet: {payload.ticker}")

    if payload.buy_date > date.today():
        raise HTTPException(status_code=400, detail="buy date can't be in the future")

    earliest_price = db.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id)
        .order_by(DailyPrice.trade_date.asc())
        .limit(1)
    ).scalar_one_or_none()
    if earliest_price is not None and payload.buy_date < earliest_price.trade_date:
        raise HTTPException(
            status_code=400,
            detail=(
                f"buy date is before the earliest data we have for "
                f"{payload.ticker} ({earliest_price.trade_date})"
            ),
        )

    holding = Holding(
        stock_id=stock.id,
        buy_price=payload.buy_price,
        quantity=payload.quantity,
        buy_date=payload.buy_date,
        created_at=datetime.utcnow(),
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)

    return _holding_response(db, holding)


@router.get("/holdings", response_model=list[HoldingResponse])
def list_holdings(db: Session = Depends(get_db)):
    holdings = db.execute(select(Holding)).scalars().all()
    return [_holding_response(db, holding) for holding in holdings]
