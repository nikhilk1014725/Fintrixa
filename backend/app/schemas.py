from datetime import datetime

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
    excluded_reason: str | None


class StockDetail(StockSummary):
    fundamental_score: float | None
    technical_score: float | None
    explanation: str | None
