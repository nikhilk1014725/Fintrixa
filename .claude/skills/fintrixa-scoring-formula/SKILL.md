---
name: fintrixa-scoring-formula
description: Use when implementing or modifying backend/scoring — defines the exact fundamental/technical scoring formula, weights, and Strong Buy/Buy/Hold/Avoid thresholds. Any scoring code change must match this spec (or update it deliberately, then re-run backtest).
---

# Fintrixa Scoring Formula

These are initial hypothesis weights, not sacred numbers — the
`backtest-agent` validates them against history and this skill should be
updated whenever the backtest justifies a re-weight. Never change weights
in `backend/scoring` without also re-running the backtest gate.

## Fundamental Score (0-100)

| Component | Points | Signal |
|---|---|---|
| Valuation | 20 | P/E vs sector average — cheaper relative to sector scores higher |
| Profitability | 20 | ROE, ROCE — higher and stable scores higher |
| Leverage | 15 | Debt/Equity — lower scores higher; near-zero debt is a bonus |
| Growth | 20 | 3-5yr revenue + profit CAGR — consistent growth scores higher than volatile growth |
| Promoter holding | 15 | Trend over last 4-8 quarters — increasing/stable holding scores higher, declining holding penalized |
| Red flags | 10 | Starts at 10, deduct for: pledged shares (>10%), auditor change in last 2yr, negative equity, going-concern note |

## Technical Trigger (0-100)

| Component | Points | Signal |
|---|---|---|
| RSI | 25 | 30-45 (recovering) or 50-65 (trending) score highest; >70 (overbought) or <20 (capitulation, no confirmation) score lowest |
| Moving averages | 30 | Price above both 50 & 200 DMA + recent golden cross scores highest; death cross scores lowest |
| Volume | 20 | Above-average volume confirming price direction scores higher than a move on thin volume |
| MACD | 25 | Bullish crossover with rising histogram scores highest |

## Combined verdicts

```
LongTermScore  = 0.70 * FundamentalScore + 0.30 * TechnicalScore
ShortTermScore = 0.70 * TechnicalScore   + 0.30 * FundamentalScore
```

## Labels

| Score | Label |
|---|---|
| 80-100 | Strong Buy |
| 60-79 | Buy |
| 40-59 | Hold |
| 0-39 | Avoid |

Every verdict ships with one plain-English sentence, e.g.:
"Strong Buy (Long-Term): consistently profitable, cheap vs peers, debt
under control — momentum is currently flat but that's not the concern
for a multi-year hold."

## Missing data rule

If any Fundamental component can't be computed (missing filing data,
newly listed stock, etc.), do not substitute 0 — exclude the stock from
ranking and surface the specific missing field as the reason. Same rule
for Technical components (e.g. insufficient price history for 200 DMA).

## Red-flag override

Regardless of the numeric score, if `news_llm` returns an active
red flag (litigation, fraud allegation, regulatory action) for a stock in
the shortlist, the verdict is capped at `Hold` even if the numeric score
says `Buy`/`Strong Buy` — surface both the score and the override reason.
