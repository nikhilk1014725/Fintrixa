from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))

    daily_prices: Mapped[list["DailyPrice"]] = relationship(back_populates="stock")
    scores: Mapped[list["Score"]] = relationship(back_populates="stock")


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    stock: Mapped["Stock"] = relationship(back_populates="daily_prices")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    fundamental_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    long_term_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    short_term_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    long_term_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    short_term_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    excluded_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="scores")
