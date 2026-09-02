"""Selects the top-N shortlist for daily news research -- the actual
cost-control enforcement point per CLAUDE.md's "LLM cost control: news_llm
only runs on the top-N shortlist, never the full universe" rule."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Score, Stock


def select_shortlist(db: Session, top_n: int) -> list[dict]:
    """Returns the top_n stocks by long_term_score (using each stock's
    most recent Score row), as [{"ticker": ..., "name": ...,
    "long_term_score": ...}], sorted descending. Stocks with no score or
    a null long_term_score are excluded -- there's nothing to shortlist
    for a stock that isn't scored."""
    stocks = db.execute(select(Stock)).scalars().all()
    scored = []
    for stock in stocks:
        stmt = (
            select(Score)
            .where(Score.stock_id == stock.id)
            .order_by(Score.computed_at.desc())
            .limit(1)
        )
        score = db.execute(stmt).scalar_one_or_none()
        if score is None or score.long_term_score is None:
            continue
        scored.append(
            {
                "ticker": stock.ticker,
                "name": stock.name,
                "long_term_score": score.long_term_score,
            }
        )
    scored.sort(key=lambda s: s["long_term_score"], reverse=True)
    return scored[:top_n]
