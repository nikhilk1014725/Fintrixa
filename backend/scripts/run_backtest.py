"""Runs the release-gate backtest for the currently-backtestable horizons
(technical/short-term only -- long-term is blocked on point-in-time
fundamentals not existing on free-tier data, see
docs/superpowers/specs/2026-09-01-backtest-foundation-design.md) and
prints the report per .claude/skills/fintrixa-backtest-methodology's
Reporting section."""
import json

from app.backtest.report import run_backtest
from app.db import SessionLocal

# Trading-day approximations: ~21 trading days/month, ~63/quarter.
HORIZONS = [
    (21, "T+1mo"),
    (63, "T+3mo"),
]


def main():
    db = SessionLocal()
    for horizon_days, label in HORIZONS:
        report = run_backtest(db, horizon_days, label)
        print(f"\n=== {label} ===")
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
