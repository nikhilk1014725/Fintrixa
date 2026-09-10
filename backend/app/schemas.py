from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    long_term_label: str | None
    short_term_label: str | None
    long_term_score: float | None
    short_term_score: float | None
    computed_at: datetime | None
    explanation: str | None
    excluded_reason: str | None


class StockDetail(StockSummary):
    fundamental_score: float | None
    technical_score: float | None
    news_confidence: str | None
    news_bull_case: str | None
    news_bear_case: str | None
    news_red_flags: list[str] | None
    news_researched_at: datetime | None
    verdict_override_reason: str | None


class PriceHistoryPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class HoldingCreate(BaseModel):
    ticker: str
    buy_price: float
    quantity: float
    buy_date: date


class HoldingGrading(BaseModel):
    verdict_in_effect: str | None
    tracking_status: str
    current_price: float | None
    price_as_of_date: date | None
    gain_loss_pct: float | None
    gain_loss_abs: float | None


class HoldingResponse(BaseModel):
    id: int
    ticker: str
    name: str
    buy_price: float
    quantity: float
    buy_date: date
    grading: HoldingGrading


class NewsDigestEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    computed_at: datetime
    confidence: str
    red_flag_count: int
