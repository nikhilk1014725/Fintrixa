"""Reads a JSON array of research-result payloads and persists them.
Last step of the daily Claude Code research routine -- see
docs/superpowers/specs/2026-09-02-news-corroboration-design.md.

Usage: python scripts/apply_news_corroboration.py path/to/results.json
"""
import json
import sys

from app.db import SessionLocal
from app.news_llm.ingest import ResearchPayloadError, validate_and_persist_research


def main():
    if len(sys.argv) != 2:
        print("usage: apply_news_corroboration.py <results.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        payloads = json.load(f)

    db = SessionLocal()
    for payload in payloads:
        try:
            corroboration = validate_and_persist_research(db, payload)
            db.commit()
            print(f"{payload.get('ticker')}: persisted, confidence={corroboration.confidence}")
        except ResearchPayloadError as e:
            db.rollback()
            print(f"{payload.get('ticker', '?')}: REJECTED - {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
