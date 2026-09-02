# Sub-project D — News Corroboration Layer — Design Spec
Date: 2026-09-02
Status: Approved

## Purpose
Per the original MVP design (`docs/superpowers/specs/2026-08-31-fintrixa-mvp-design.md`)
and `.claude/skills/fintrixa-scoring-formula`'s "Red-flag override" section:
research the top-5 shortlist (by long-term score) daily, summarize bull/bear
case, flag active red flags (litigation, fraud allegation, regulatory
action), and cap a stock's displayed verdict at `Hold` when a red flag is
active — regardless of what the numeric score says.

**User-approved architecture, differing from the original tech-stack doc's
assumption of a backend `anthropic` SDK client:** the research itself is
performed by a **Claude Code scheduled routine**, not by backend Python
code calling the Anthropic API. No `ANTHROPIC_API_KEY` in the backend, no
separate pay-per-token billing — the daily task uses whatever Claude access
this CLI session already has, via Claude Code's own `WebSearch` tool. This
still satisfies "uses the operator's existing Claude access; no separate
paid LLM subscription" — more directly than an API-key-based integration
would have. Cost control (top-N only, N=5) is enforced by construction: the
routine only ever researches the shortlist the DB hands it.

## What backend/app/news_llm/ actually owns
Since the LLM call happens outside Python, this module's job is the data
contract and logic around news corroboration, not the LLM call itself:

- **`shortlist.py`** — `select_shortlist(db, top_n) -> list[dict]`: query
  the latest `Score` per stock (same pattern as `routes.py`'s
  `_latest_score`), filter to non-null `long_term_score`, sort descending,
  return the top N as `[{"ticker": ..., "name": ..., "long_term_score": ...}]`.
  This is what the scheduled routine reads to know which 5 tickers to
  research today — it is the actual cost-control enforcement point.
- **`ingest.py`** — `validate_and_persist_research(db, payload) -> NewsCorroboration`:
  validates a research-result payload (ticker, bull_case, bear_case,
  red_flags, confidence, sources) and persists it. Confidence must be
  exactly one of `Corroborated` / `Mixed` / `Unconfirmed` (per the
  original design's exact tag set) — reject anything else with a clear
  error rather than silently coercing. Unknown ticker → clear error, not
  a silent no-op.
- **`override.py`** — `apply_red_flag_override(score, corroboration) -> dict`:
  pure function. Given a `Score` row and the stock's latest
  `NewsCorroboration` (or `None` if never researched), returns the
  *effective* `long_term_label`/`short_term_label` to display plus an
  `override_reason` (`None` unless a cap was actually applied). Red flags
  only ever cap a label *down* (`Strong Buy`/`Buy` → `Hold`), never raise
  one — matches the scoring-formula skill's exact wording.

### New DB model: `NewsCorroboration` (`backend/app/models.py`)
`id, stock_id (FK), computed_at, bull_case (Text), bear_case (Text),
red_flags (JSON list[str], empty list if none found), confidence
(String — one of the three tags), sources (JSON list of
{"title": str, "url": str})`. New Alembic migration.

### New scripts (`backend/scripts/`)
- **`get_shortlist.py`** — prints `select_shortlist(db, top_n=5)` as JSON.
  The Claude Code routine's first step: run this to know what to research.
- **`apply_news_corroboration.py`** — reads a JSON array of research-result
  payloads (one per researched stock) from a file path argument, calls
  `validate_and_persist_research` for each, prints a per-ticker
  confirmation. The routine's last step, after it has done the actual
  research via `WebSearch`.

### API changes (`backend/app/api/`)
`StockDetail` gains: `news_confidence: str | None`, `news_bull_case: str |
None`, `news_bear_case: str | None`, `news_red_flags: list[str] | None`,
`news_researched_at: datetime | None`, `verdict_override_reason: str |
None`. All `None` when the stock has never been researched — distinct from
`news_confidence == "Unconfirmed"`, which is itself a real research
*outcome*, not an absence of research. `stock_detail()` fetches the
latest `NewsCorroboration` alongside the latest `Score`, calls
`apply_red_flag_override`, and returns the *effective* (possibly capped)
labels in `long_term_label`/`short_term_label` — the API never exposes an
overridden-but-unlabeled-as-such value; `verdict_override_reason` always
explains a cap when one is present.

### Frontend changes (`frontend/src/components/StockDetail.tsx`)
- If `news_red_flags` is non-empty: a Level-1 (always visible, not behind
  "Show details") warning card — red flags are safety-relevant, hiding them
  behind a click contradicts the "don't hide risk" principle already
  established for this app. Shows the flags and, if present,
  `verdict_override_reason`.
- If `news_researched_at` is set but no red flags: bull/bear case and the
  confidence tag go in the existing Level 2 "Show details" section,
  alongside the score breakdown — this is exactly the kind of "advanced
  research" depth that section already holds.
- If `news_researched_at` is `None` (never researched — true for 95 of the
  100 tracked stocks at any time, since only the top-5 shortlist gets
  researched): show nothing news-related at all. No "not yet researched"
  placeholder clutter — matches the established Phase A convention (no
  field without a real backing value).

## The scheduled routine (set up last, via the `schedule` skill)
A daily Claude Code cron routine whose prompt: (1) runs
`get_shortlist.py` to get today's 5 tickers, (2) uses `WebSearch` to
research each — recent news (≈30 days), filings, analyst commentary —
producing bull case, bear case, red flags (litigation/fraud/regulatory
only — not every negative headline), and a confidence tag, (3) writes the
results as a JSON payload and runs `apply_news_corroboration.py` with it.
Manually dry-run this once before relying on the schedule, to confirm the
prompt actually produces a valid payload the ingest script accepts.

## Testing
- `shortlist.py`, `ingest.py`, `override.py`: unit tests with an in-memory
  sqlite DB (existing fixture pattern), no network/LLM calls anywhere in
  the test suite (there's nothing to mock — the LLM call isn't in Python).
- `override.py` specifically: test the cap-down-only behavior (Strong
  Buy/Buy → Hold on an active red flag; Hold/Avoid unchanged; no
  corroboration → no override; corroboration with empty `red_flags` → no
  override even if confidence is `Unconfirmed`).
- `ingest.py`: reject an invalid confidence value, reject an unknown
  ticker, accept a valid payload and confirm the row lands correctly.
- API: extend existing route tests to cover a stock with an active red
  flag (labels capped, reason present) and a stock never researched (all
  news fields `None`).
- Frontend: extend `StockDetail.test.tsx` for the red-flag card (always
  visible) and the Level-2 bull/bear/confidence section.

## Explicitly out of scope
The scheduled routine's exact prompt wording is tuned live during the
manual dry-run, not fully hand-specified here. Any change to the numeric
scoring formula (this only affects the *displayed label*, per the
scoring-formula skill's own framing — the override caps presentation, not
the underlying score). Sources/citations UI polish beyond storing them
(no dedicated "Sources & Research" page yet — that's later, closer to
newIdea.md §38). Any use of the red-flag data as a *positive* signal —
only the cap-down override is implemented, matching the spec.
