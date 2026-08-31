# Fintrixa — Decisions Log

Running log of decisions/constraints an agent (or future you) needs
before touching this codebase. Newest first.

## 2026-08-31 — Local dev environment: Postgres 16 via Homebrew, Python 3.11
System `python3` is 3.9.6 (too old — project needs >=3.11); use
`/opt/homebrew/bin/python3.11` for the backend venv. Postgres 16 runs via
`brew services start postgresql@16`, with a `fintrixa`/`fintrixa` db/user
already created locally matching `settings.database_url`. **Why:**
neither was present on the machine when the walking skeleton was built.
**How to apply:** if Postgres isn't running (`pg_isready` fails), run
`brew services start postgresql@16` before touching the backend.

## 2026-08-31 — Walking skeleton confirms yfinance fundamentals are thin, even for large-caps
Running the seed script live against RELIANCE.NS (India's largest
company by market cap) returned no `sector_pe` and no `return_on_equity`
from yfinance — the fundamental score was correctly excluded rather than
guessed. **Why this matters:** validates the "no silent zero-score" rule
end-to-end against real data, and confirms the ingestion-breadth plan's
screener.in fallback isn't optional polish — without it, most/all stocks
will show `excluded_reason` for the long-term verdict. **How to apply:**
prioritize `sector_pe` and `return_on_equity` in the screener.in fallback
first — those are the two fields that just failed on a blue-chip.

## 2026-08-31 — Signal-color exception to the lavender/white/black palette
Buy/Hold/Avoid verdict badges use green/red accent colors, everything
else stays lavender/white/black. **Why:** a layman needs to recognize
buy-vs-avoid instantly; subtle lavender shading isn't safe for that.
**Flag:** revisit if strict 3-color purity turns out to matter more than
instant signal recognition — this was an assumption call, not confirmed
with the user.

## 2026-08-31 — LLM news layer uses existing Claude access, not a new subscription
`news_llm` calls route through the operator's existing Claude access,
invoked only on the top-N shortlist. **Why:** "free-tier only" budget
answer + LLM summarization requirement can't both be satisfied by a
dedicated paid subscription. **How to apply:** any future move to a
different/paid LLM provider needs explicit sign-off first.

## 2026-08-31 — Modular monolith architecture chosen
One FastAPI app / one Postgres DB / module-separated code
(`ingestion`/`scoring`/`backtest`/`news_llm`/`api`/`frontend`), over a
jobs+API split or full microservices. **Why:** single user, free-tier,
personal MVP — simplest to run and maintain, module boundaries already
clean enough to split into services later if this ever goes public.
**How to apply:** don't add service-to-service infra (queues, separate
deploys) until there's an actual second user or scale need.

## 2026-08-31 — Backtest is a release gate, not a nice-to-have
No scoring-formula change ships without passing the hit-rate threshold
in `.claude/skills/fintrixa-backtest-methodology`. **Why:** score
outputs drive real buy/sell decisions; an untested formula change is a
correctness risk, not just a code-quality one. **How to apply:** the
`qa-agent` checks for backtest evidence before signing off any
`scoring` change.
