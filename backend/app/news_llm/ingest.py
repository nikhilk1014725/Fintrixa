"""Validates and persists a research-result payload from the daily news
research routine. The LLM call itself happens outside this codebase (a
Claude Code scheduled routine, see
docs/superpowers/specs/2026-09-02-news-corroboration-design.md) -- this
module only owns the data contract and persistence."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NewsCorroboration, Stock

VALID_CONFIDENCE_TAGS = {"Corroborated", "Mixed", "Unconfirmed"}


class ResearchPayloadError(ValueError):
    """Raised when a research-result payload fails validation."""


def validate_and_persist_research(db: Session, payload: dict) -> NewsCorroboration:
    """payload: {"ticker": str, "bull_case": str, "bear_case": str,
    "red_flags": list[str], "confidence": str, "sources": list[{"title":
    str, "url": str}]}. Raises ResearchPayloadError on any invalid field
    -- never silently coerces or drops a bad payload. Does not commit --
    caller controls the transaction."""
    ticker = payload.get("ticker")
    if not ticker:
        raise ResearchPayloadError("payload missing 'ticker'")

    stock = db.execute(select(Stock).where(Stock.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        raise ResearchPayloadError(f"unknown ticker: {ticker}")

    confidence = payload.get("confidence")
    if confidence not in VALID_CONFIDENCE_TAGS:
        raise ResearchPayloadError(
            f"invalid confidence '{confidence}', must be one of {sorted(VALID_CONFIDENCE_TAGS)}"
        )

    bull_case = payload.get("bull_case")
    bear_case = payload.get("bear_case")
    if not bull_case or not bear_case:
        raise ResearchPayloadError("payload missing 'bull_case' or 'bear_case'")

    red_flags = payload.get("red_flags", [])
    if not isinstance(red_flags, list):
        raise ResearchPayloadError("'red_flags' must be a list")
    if not all(isinstance(flag, str) and flag for flag in red_flags):
        raise ResearchPayloadError("every 'red_flags' entry must be a non-empty string")

    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ResearchPayloadError("'sources' must be a list")
    if not all(
        isinstance(s, dict) and s.get("title") and s.get("url")
        for s in sources
    ):
        raise ResearchPayloadError("every 'sources' entry must be a dict with non-empty 'title' and 'url'")

    corroboration = NewsCorroboration(
        stock_id=stock.id,
        computed_at=datetime.utcnow(),
        bull_case=bull_case,
        bear_case=bear_case,
        red_flags=red_flags,
        confidence=confidence,
        sources=sources,
    )
    db.add(corroboration)
    db.flush()
    return corroboration
