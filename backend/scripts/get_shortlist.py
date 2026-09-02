"""Prints today's news-research shortlist as JSON. First step of the
daily Claude Code research routine -- see
docs/superpowers/specs/2026-09-02-news-corroboration-design.md."""
import json
import sys

from app.db import SessionLocal
from app.news_llm.shortlist import select_shortlist

TOP_N = 5


def main():
    db = SessionLocal()
    shortlist = select_shortlist(db, top_n=TOP_N)
    json.dump(shortlist, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
