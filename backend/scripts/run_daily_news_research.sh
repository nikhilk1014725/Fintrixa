#!/bin/bash
# Daily news-research routine: runs Claude Code headlessly to research the
# top-15 shortlist and persist results. Local (not a cloud Routine) because
# it needs direct access to the local Postgres DB -- see
# docs/superpowers/specs/2026-09-02-news-corroboration-design.md and
# docs/DECISIONS.md (2026-09-02 entry on why this isn't a cloud Routine).
set -euo pipefail

PROJECT_DIR="/Users/nikhilkumar/Projects/Fintrixa"
CLAUDE_BIN="/Users/nikhilkumar/.nvm/versions/node/v24.16.0/bin/claude"
LOG_DIR="$PROJECT_DIR/backend/logs"
mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

PROMPT='Run the daily Fintrixa news-research routine:
1. cd backend && .venv/bin/python scripts/get_shortlist.py -- this prints the top-15 shortlist as JSON.
2. For each ticker in the shortlist, use WebSearch to research recent news (last ~30 days), filings, and analyst commentary. Produce: a bull_case (1-2 sentences), a bear_case (1-2 sentences), red_flags (a list of strings -- ONLY active litigation, fraud allegations, or regulatory actions; do not include routine negative news, analyst downgrades, or general sector weakness), a confidence tag (exactly one of "Corroborated" if multiple independent sources agree, "Mixed" if sources conflict, or "Unconfirmed" if coverage is thin/single-source), and sources (list of {"title": ..., "url": ...}).
3. Write the results as a JSON array (one object per ticker, matching this shape: {"ticker": ..., "bull_case": ..., "bear_case": ..., "red_flags": [...], "confidence": ..., "sources": [...]}) to a temp file, then run: cd backend && .venv/bin/python scripts/apply_news_corroboration.py <path to that temp file>
4. Report which tickers were persisted successfully and which (if any) were rejected, and why.

Be factual and conservative about red_flags -- only flag genuine litigation/fraud/regulatory action, never routine market commentary.'

"$CLAUDE_BIN" -p "$PROMPT" --allowedTools "Bash,WebSearch" >> "$LOG_DIR/news_research_$(date +%Y%m%d_%H%M%S).log" 2>&1
