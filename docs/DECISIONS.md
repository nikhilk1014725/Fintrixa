# Fintrixa — Decisions Log

Running log of decisions/constraints an agent (or future you) needs
before touching this codebase. Newest first.

## 2026-09-02 — Daily news-research routine runs via local launchd, not a Claude Code cloud Routine
Considered Claude Code's `schedule` skill (cloud Routines, `RemoteTrigger`)
for the daily news-corroboration task. Confirmed via Anthropic's own blog
post ("Introducing routines in Claude Code") that Routines "run on Claude
Code's web infrastructure, so nothing depends on your laptop being open" —
i.e. an isolated cloud sandbox with no access to this project's local
Postgres DB (`localhost:5432`). `apply_news_corroboration.py`'s write-back
step would fail on every scheduled run. **Why not fixed by exposing the
DB:** this project's CLAUDE.md/DECISIONS.md assume localhost-only; opening
a personal DB to the internet for this is a real security tradeoff not
worth taking for a convenience feature.

**Decision:** a macOS `launchd` job (`~/Library/LaunchAgents/com.fintrixa.
news-research.plist`, not checked into the repo — machine-specific) fires
`backend/scripts/run_daily_news_research.sh` at 08:00 IST on 6 explicit
dates (Sep 3-8, 2026, per user request — a bounded trial, not an
open-ended schedule) via 6 `StartCalendarInterval` entries rather than a
recurring rule; it naturally stops firing after Sep 8 with no extra
unload logic needed. To extend it, add more date entries and re-`load`
the plist (`launchctl unload` then `load` picks up edits — a bare re-load
without unload does not). That script runs `claude -p "<prompt>"`
headlessly (`--allowedTools Bash,WebSearch`) — Claude Code's local CLI,
not a cloud session — so it has direct filesystem/DB access exactly like
an interactive session would. Logs land in `backend/logs/` (gitignored).

**How to apply:** to inspect/modify the schedule, edit the plist directly
or `launchctl unload`/`load` it. To change the research prompt, edit
`run_daily_news_research.sh`, not the plist. The dry run that proved this
pipeline works end-to-end (5 real stocks researched, 3 genuine red flags
found — RBI penalty on Muthoot Finance, DXC litigation on TCS, DLF Home
Developers Supreme Court matter — verdicts correctly capped via the API)
was done manually before this schedule was set up; the first real
automated firing should still be checked, not assumed to have worked.

## 2026-09-02 — Completing the Technical Trigger (Volume+MACD) did not close the gate — still FAILS
Implemented the two missing components (Volume 20pts, MACD 25pts — see
`docs/superpowers/specs/2026-09-02-complete-technical-trigger-design.md`)
and re-ran the same backtest harness against the same price history. New
results, compared to the RSI+MA-only baseline immediately below:

- **T+1mo**: 119 usable windows. Top-quartile pass rate **65.5%**
  (unchanged from baseline). Bottom-quartile pass rate **40.3%**
  (unchanged from baseline). **Still FAIL.**
- **T+3mo**: 118 usable windows. Top-quartile pass rate **66.9%** (down
  from 69.5%). Bottom-quartile pass rate **33.9%** (down from 36.4%).
  **Still FAIL, and slightly worse than baseline.**

Verified this is a real result, not a bug: confirmed the new formula is
actually active (spot-checked real stock/date combinations — Volume and
MACD point buckets vary meaningfully across dates, not stuck at a constant
or silently falling back to the old behavior).

**Why this matters:** RSI, moving averages, volume-confirmation, and MACD
are all derived from the same underlying price momentum — for most stocks
they move together (a stock in a strong uptrend tends to show favorable
RSI, a golden cross, confirming volume, AND a bullish MACD simultaneously).
Adding more momentum-flavored components didn't materially change which
stocks land in the top/bottom quartile, because they weren't adding
independent information, just correlated confirmation of the same signal.
The formula's core asymmetry — good at spotting winners, unable to flag
losers — is not a "missing component" problem; it looks structural.

**How to apply:** per the design spec's own instruction, no further ad hoc
tweaking in this sitting — that risks overfitting to this specific
backtest window. This remains a product decision, now with more evidence:
(a) a genuinely independent signal type is likely needed to catch
downside (e.g. fundamentals-based red flags via `news_llm`, once built,
or a mean-reversion/volatility signal uncorrelated with trend-following
indicators) rather than another trend indicator; (b) accept the asymmetry
and scope any near-term feature to the validated side only (surfacing
"opportunity" candidates from the top quartile, explicitly not claiming
an "Avoid" signal has been backtested); (c) revisit whether quartile
symmetry is even the right release-gate design for a formula that's
fundamentally trend-following by construction. Sub-project C's next stage
stays blocked until one of these is decided.

## 2026-09-02 — First backtest release-gate result: current technical formula FAILS, asymmetrically
Ran the new `backend/backtest` harness (`scripts/run_backtest.py`) against
the deepened price history (`scripts/backfill_price_history.py`, `period=
"max"`, 1991-2026, ~100 NSE stocks, median ~24yr/stock) for both
backtestable horizons. Results:

- **T+1mo**: 119 usable windows. Top-quartile pass rate **65.5%** (clears
  the 60% gate). Bottom-quartile pass rate **40.3%** (fails badly).
  **Overall: FAIL** (both conditions required).
- **T+3mo**: 118 usable windows. Top-quartile pass rate **69.5%** (clears).
  Bottom-quartile pass rate **36.4%** (fails). **Overall: FAIL**.

**Why this matters:** the formula being tested is only the RSI + 50/200-DMA
portion of the Technical Trigger (`backend/app/scoring/technical.py`) —
volume and MACD (45 of the spec's 100 points) aren't implemented yet. The
result isn't "no signal" — it's asymmetric: the formula reliably identifies
stocks that will outperform (top quartile), but has close to no ability to
flag stocks that will underperform (bottom quartile performs worse than
chance at being "below median," which is the opposite of what a working
Avoid signal should do). Long-term/fundamental horizons remain
**unvalidated by design** — no point-in-time fundamentals source exists
on free-tier data, so they were never attempted (see
`docs/superpowers/specs/2026-09-01-backtest-foundation-design.md`).

**How to apply:** per CLAUDE.md's non-negotiable backtest gate, this
formula does not currently clear release. Any UI or feature that implies
the current formula reliably flags "Avoid"/downside risk (confidence
scores, risk narratives, holding-period recommendations derived from the
combined score) would misrepresent what's actually validated — don't build
those on top of this formula as-is. Before sub-project C's confidence/
holding-period/forecast work proceeds, either (a) complete the Technical
Trigger (volume + MACD) and re-run this backtest, or (b) reweight/redesign
the existing two components, or (c) explicitly scope any near-term feature
to only the validated side of the signal (top-quartile "opportunity"
surfacing) and say so plainly, not silently. This is a product decision,
not an engineering one — flagged for the operator, not decided here.

## 2026-08-31 — Frontend dev-server vulnerabilities in esbuild/vite: accepted, not fixed
`npm audit` flags esbuild <=0.24.2 (moderate/high/critical chain into
vite/vitest) — the dev server accepts cross-origin requests. **Why not
fixed:** the fix is a breaking major-version jump to Vite 8, and this is
a localhost-only personal MVP, never exposed to an untrusted network.
**How to apply:** revisit before ever exposing the dev server beyond
localhost (e.g. `--host`, tunneling, deployment) — don't carry this
acceptance into a public-facing setup without re-evaluating.

## 2026-08-31 — Implementer subagents can report DONE on work that doesn't actually run
The first UI-overhaul implementer created all component files correctly
but never installed Tailwind or wired the Vite plugin — the built CSS
was 0.06kB (empty) despite a "DONE" report and a passing `npm run build`
(Vite doesn't error just because Tailwind generated nothing). **Why this
matters:** build success and test pass are necessary but not sufficient
— always spot-check actual output artifacts (bundle sizes, rendered
content) before trusting a subagent's self-report, especially for
multi-step environment/tooling setup tasks. **How to apply:** for any
future build-tooling change, check `dist/assets/*.css` (or equivalent)
size and content directly, don't just check the build exited 0.

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
