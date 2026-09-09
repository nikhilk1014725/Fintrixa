"""Grades a logged holding against the AI verdict that was in effect when
it was bought, per docs/superpowers/specs/2026-09-09-my-holdings-tracker-
design.md. Never fabricates a verdict or a price -- both surface an
explicit absent/stale state instead."""
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyPrice, Holding, Score

BULLISH_LABELS = {"Strong Buy", "Buy"}

TRACKING_AS_EXPECTED = "tracking_as_expected"
NOT_TRACKING_AS_EXPECTED = "not_tracking_as_expected"
NO_BULLISH_CALL = "no_bullish_call"
NO_CALL_ON_RECORD = "no_call_on_record"


def _verdict_in_effect(db: Session, stock_id: int, buy_date: date) -> Score | None:
    cutoff = datetime.combine(buy_date, time.max)
    stmt = (
        select(Score)
        .where(Score.stock_id == stock_id, Score.computed_at <= cutoff)
        .order_by(Score.computed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _latest_price(db: Session, stock_id: int) -> DailyPrice | None:
    stmt = (
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock_id)
        .order_by(DailyPrice.trade_date.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def grade_holding(db: Session, holding: Holding) -> dict:
    """Returns {"verdict_in_effect", "tracking_status", "current_price",
    "price_as_of_date", "gain_loss_pct", "gain_loss_abs"}."""
    score = _verdict_in_effect(db, holding.stock_id, holding.buy_date)
    price = _latest_price(db, holding.stock_id)

    current_price = price.close if price else None
    price_as_of_date = price.trade_date if price else None

    gain_loss_pct = None
    gain_loss_abs = None
    if current_price is not None:
        gain_loss_pct = round((current_price - holding.buy_price) / holding.buy_price * 100, 2)
        gain_loss_abs = round((current_price - holding.buy_price) * holding.quantity, 2)

    if score is None:
        return {
            "verdict_in_effect": None,
            "tracking_status": NO_CALL_ON_RECORD,
            "current_price": current_price,
            "price_as_of_date": price_as_of_date,
            "gain_loss_pct": gain_loss_pct,
            "gain_loss_abs": gain_loss_abs,
        }

    long_bullish = score.long_term_label in BULLISH_LABELS
    short_bullish = score.short_term_label in BULLISH_LABELS
    bullish = long_bullish or short_bullish

    if long_bullish:
        verdict_in_effect = score.long_term_label
    elif short_bullish:
        verdict_in_effect = score.short_term_label
    else:
        verdict_in_effect = score.long_term_label or score.short_term_label

    if not bullish or gain_loss_pct is None:
        tracking_status = NO_BULLISH_CALL
    elif gain_loss_pct >= 0:
        tracking_status = TRACKING_AS_EXPECTED
    else:
        tracking_status = NOT_TRACKING_AS_EXPECTED

    return {
        "verdict_in_effect": verdict_in_effect,
        "tracking_status": tracking_status,
        "current_price": current_price,
        "price_as_of_date": price_as_of_date,
        "gain_loss_pct": gain_loss_pct,
        "gain_loss_abs": gain_loss_abs,
    }
