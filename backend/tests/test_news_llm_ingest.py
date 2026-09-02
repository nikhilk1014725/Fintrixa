import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import NewsCorroboration, Stock
from app.news_llm.ingest import ResearchPayloadError, validate_and_persist_research


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def _valid_payload(ticker="TCS.NS"):
    return {
        "ticker": ticker,
        "bull_case": "Strong order book, margin expansion.",
        "bear_case": "Client concentration risk in BFSI.",
        "red_flags": [],
        "confidence": "Corroborated",
        "sources": [{"title": "Q2 results", "url": "https://example.com/q2"}],
    }


def test_validate_and_persist_research_valid_payload(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    corroboration = validate_and_persist_research(db_session, _valid_payload())

    assert corroboration.stock_id == stock.id
    assert corroboration.confidence == "Corroborated"
    assert db_session.query(NewsCorroboration).count() == 1


def test_validate_and_persist_research_rejects_invalid_confidence(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    payload = _valid_payload()
    payload["confidence"] = "Very Sure"

    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, payload)


def test_validate_and_persist_research_rejects_unknown_ticker(db_session):
    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, _valid_payload(ticker="NOPE.NS"))


def test_validate_and_persist_research_rejects_missing_bull_or_bear_case(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    payload = _valid_payload()
    payload["bull_case"] = ""

    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, payload)


def test_validate_and_persist_research_rejects_non_string_red_flag(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    payload = _valid_payload()
    payload["red_flags"] = [123]

    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, payload)


def test_validate_and_persist_research_rejects_source_missing_url(db_session):
    stock = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    db_session.add(stock)
    db_session.commit()

    payload = _valid_payload()
    payload["sources"] = [{"title": "Some article"}]

    with pytest.raises(ResearchPayloadError):
        validate_and_persist_research(db_session, payload)
