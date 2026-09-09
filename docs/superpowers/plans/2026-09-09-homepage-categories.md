# Homepage Categories + Card One-Liner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the homepage into 3 honest category sections (Best Today / Long-Term Picks / Short-Term Picks) and show the plain-English `explanation` one-liner on every stock card, using only fields the API already computes.

**Architecture:** One additive backend field (`explanation` on the `/stocks` list response, already computed and already exposed on the detail endpoint) flows through the existing `StockSummary` type into two frontend components: `StockCard` (renders it) and `Home` (uses existing scores/labels to bucket stocks into 3 filtered+sorted sections, each with type-safe filters matching the codebase's existing type-predicate pattern, no `??` fallbacks).

**Tech Stack:** FastAPI + Pydantic (backend), React + TypeScript + Vitest/RTL (frontend).

Spec: `docs/superpowers/specs/2026-09-09-homepage-categories-design.md`

---

### Task 1: Expose `explanation` on the `/stocks` list endpoint

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py` (after `test_stock_detail_returns_full_breakdown`):

```python
def test_list_stocks_includes_explanation_matching_detail_endpoint(client):
    list_response = client.get("/stocks")
    detail_response = client.get("/stocks/RELIANCE.NS")
    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    list_body = list_response.json()
    detail_body = detail_response.json()
    assert list_body[0]["explanation"] == "Long-term: buy on fundamentals (82/100)..."
    assert list_body[0]["explanation"] == detail_body["explanation"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_routes.py::test_list_stocks_includes_explanation_matching_detail_endpoint -v`
Expected: FAIL with `KeyError: 'explanation'`

- [ ] **Step 3: Add `explanation` to `StockSummary` and remove the now-duplicate field from `StockDetail`**

In `backend/app/schemas.py`, change:

```python
class StockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    long_term_label: str | None
    short_term_label: str | None
    long_term_score: float | None
    short_term_score: float | None
    computed_at: datetime | None
    excluded_reason: str | None


class StockDetail(StockSummary):
    fundamental_score: float | None
    technical_score: float | None
    explanation: str | None
    news_confidence: str | None
```

to:

```python
class StockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    long_term_label: str | None
    short_term_label: str | None
    long_term_score: float | None
    short_term_score: float | None
    computed_at: datetime | None
    explanation: str | None
    excluded_reason: str | None


class StockDetail(StockSummary):
    fundamental_score: float | None
    technical_score: float | None
    news_confidence: str | None
```

- [ ] **Step 4: Include `explanation` in the list-endpoint response**

In `backend/app/api/routes.py`, in `list_stocks`, change:

```python
        results.append(
            StockSummary(
                ticker=stock.ticker,
                name=stock.name,
                long_term_label=override["long_term_label"],
                short_term_label=override["short_term_label"],
                long_term_score=score.long_term_score if score else None,
                short_term_score=score.short_term_score if score else None,
                computed_at=score.computed_at if score else None,
                excluded_reason=score.excluded_reason if score else "not yet scored",
            )
        )
```

to:

```python
        results.append(
            StockSummary(
                ticker=stock.ticker,
                name=stock.name,
                long_term_label=override["long_term_label"],
                short_term_label=override["short_term_label"],
                long_term_score=score.long_term_score if score else None,
                short_term_score=score.short_term_score if score else None,
                computed_at=score.computed_at if score else None,
                explanation=score.explanation if score else None,
                excluded_reason=score.excluded_reason if score else "not yet scored",
            )
        )
```

Also remove the now-redundant `explanation=score.explanation if score else None,` line from the `StockDetail(...)` construction in `stock_detail` — leave it as is; it's harmless (Pydantic accepts it since `StockDetail` still has the field inherited). **Do not remove it** — removing it would require re-verifying the detail endpoint still passes; it's redundant but correct to leave. Skip this sub-step.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_routes.py -v`
Expected: `9 passed` (8 existing + 1 new)

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/api/routes.py backend/tests/test_routes.py
git commit -m "feat: expose explanation on the /stocks list endpoint"
```

---

### Task 2: Add `explanation` to the frontend `StockSummary` type

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/components/Discover.test.tsx`
- Modify: `frontend/src/components/StockCard.test.tsx`
- Modify: `frontend/src/components/Home.test.tsx`

This task is a mechanical type-safety update: `explanation` becomes a required key (value may be `null`) on `StockSummary`, so every existing object literal typed as `StockSummary` must include it. No behavior changes yet — that's Tasks 3 and 4.

- [ ] **Step 1: Add the field to the type, remove the now-duplicate field from `StockDetail`**

In `frontend/src/api/client.ts`, change:

```ts
export interface StockSummary {
  ticker: string;
  name: string;
  long_term_label: string | null;
  short_term_label: string | null;
  long_term_score: number | null;
  short_term_score: number | null;
  computed_at: string | null;
  excluded_reason: string | null;
}

export interface StockDetail extends StockSummary {
  fundamental_score: number | null;
  technical_score: number | null;
  explanation: string | null;
  news_confidence: string | null;
  news_bull_case: string | null;
  news_bear_case: string | null;
  news_red_flags: string[] | null;
  news_researched_at: string | null;
  verdict_override_reason: string | null;
}
```

to:

```ts
export interface StockSummary {
  ticker: string;
  name: string;
  long_term_label: string | null;
  short_term_label: string | null;
  long_term_score: number | null;
  short_term_score: number | null;
  computed_at: string | null;
  explanation: string | null;
  excluded_reason: string | null;
}

export interface StockDetail extends StockSummary {
  fundamental_score: number | null;
  technical_score: number | null;
  news_confidence: string | null;
  news_bull_case: string | null;
  news_bear_case: string | null;
  news_red_flags: string[] | null;
  news_researched_at: string | null;
  verdict_override_reason: string | null;
}
```

- [ ] **Step 2: Run the type checker to confirm it now fails on existing fixtures**

Run: `cd frontend && npx tsc --noEmit`
Expected: several errors like `Property 'explanation' is missing in type '{ ticker: string; ... }' but required in type 'StockSummary'` in `App.test.tsx`, `Discover.test.tsx`, `StockCard.test.tsx`, `Home.test.tsx`.

- [ ] **Step 3: Fix `App.test.tsx`**

In `frontend/src/App.test.tsx`, change:

```tsx
const stocks: StockSummary[] = [
  {
    ticker: "TCS.NS",
    name: "Tata Consultancy Services",
    long_term_label: "Buy",
    short_term_label: "Hold",
    long_term_score: 78.4,
    short_term_score: 55.0,
    computed_at: "2026-08-31T18:00:00Z",
    excluded_reason: null,
  },
];
```

to:

```tsx
const stocks: StockSummary[] = [
  {
    ticker: "TCS.NS",
    name: "Tata Consultancy Services",
    long_term_label: "Buy",
    short_term_label: "Hold",
    long_term_score: 78.4,
    short_term_score: 55.0,
    computed_at: "2026-08-31T18:00:00Z",
    explanation: null,
    excluded_reason: null,
  },
];
```

(The other two inline stock arrays later in this file are cast `as any`, so they don't need the field — leave them unchanged.)

- [ ] **Step 4: Fix `Discover.test.tsx`**

In `frontend/src/components/Discover.test.tsx`, change:

```tsx
const stocks: StockSummary[] = [
  {
    ticker: "RELIANCE.NS",
    name: "Reliance Industries",
    long_term_label: null,
    short_term_label: null,
    long_term_score: null,
    short_term_score: null,
    computed_at: null,
    excluded_reason: "missing required fundamental fields: sector_pe, return_on_equity",
  },
];
```

to:

```tsx
const stocks: StockSummary[] = [
  {
    ticker: "RELIANCE.NS",
    name: "Reliance Industries",
    long_term_label: null,
    short_term_label: null,
    long_term_score: null,
    short_term_score: null,
    computed_at: null,
    explanation: null,
    excluded_reason: "missing required fundamental fields: sector_pe, return_on_equity",
  },
];
```

- [ ] **Step 5: Fix `StockCard.test.tsx`**

In `frontend/src/components/StockCard.test.tsx`, change:

```tsx
const stock: StockSummary = {
  ticker: "TCS.NS",
  name: "Tata Consultancy Services",
  long_term_label: "Buy",
  short_term_label: "Hold",
  long_term_score: 78.4,
  short_term_score: 55.0,
  computed_at: "2026-08-31T18:00:00Z",
  excluded_reason: null,
};
```

to:

```tsx
const stock: StockSummary = {
  ticker: "TCS.NS",
  name: "Tata Consultancy Services",
  long_term_label: "Buy",
  short_term_label: "Hold",
  long_term_score: 78.4,
  short_term_score: 55.0,
  computed_at: "2026-08-31T18:00:00Z",
  explanation: "Strong business, healthy balance sheet, attractive long-term growth potential.",
  excluded_reason: null,
};
```

(Task 3 adds the tests that actually exercise this field; this step only makes the file compile.)

- [ ] **Step 6: Fix `Home.test.tsx`**

In `frontend/src/components/Home.test.tsx`, add `explanation: null,` to each of the three inline `StockSummary` object literals (`scored`, `excluded`, `higher`) — e.g. change:

```tsx
const scored: StockSummary = {
  ticker: "TCS.NS",
  name: "Tata Consultancy Services",
  long_term_label: "Buy",
  short_term_label: "Hold",
  long_term_score: 78.4,
  short_term_score: 55.0,
  computed_at: "2026-08-31T18:00:00Z",
  excluded_reason: null,
};
```

to:

```tsx
const scored: StockSummary = {
  ticker: "TCS.NS",
  name: "Tata Consultancy Services",
  long_term_label: "Buy",
  short_term_label: "Hold",
  long_term_score: 78.4,
  short_term_score: 55.0,
  computed_at: "2026-08-31T18:00:00Z",
  explanation: null,
  excluded_reason: null,
};
```

Do the same for `excluded` and `higher`. (Task 4 replaces this whole file's test bodies with the category-section tests; this step only keeps it compiling until then.)

- [ ] **Step 7: Run the type checker and full test suite to confirm everything passes**

Run: `cd frontend && npx tsc --noEmit && npm test`
Expected: `tsc` exits with no output (success); `npm test` shows all existing test files passing, no new failures.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/App.test.tsx frontend/src/components/Discover.test.tsx frontend/src/components/StockCard.test.tsx frontend/src/components/Home.test.tsx
git commit -m "feat: add explanation field to the frontend StockSummary type"
```

---

### Task 3: Render the explanation one-liner on `StockCard`

**Files:**
- Modify: `frontend/src/components/StockCard.tsx`
- Test: `frontend/src/components/StockCard.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add to `frontend/src/components/StockCard.test.tsx` (after the existing three tests):

```tsx
test("renders the explanation sentence when present", () => {
  render(<StockCard stock={stock} onSelect={vi.fn()} />);
  expect(
    screen.getByText(
      "Strong business, healthy balance sheet, attractive long-term growth potential."
    )
  ).toBeInTheDocument();
});

test("renders nothing extra when explanation is null", () => {
  const noExplanation: StockSummary = { ...stock, explanation: null };
  render(<StockCard stock={noExplanation} onSelect={vi.fn()} />);
  expect(
    screen.queryByText(
      "Strong business, healthy balance sheet, attractive long-term growth potential."
    )
  ).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- StockCard`
Expected: FAIL — "renders the explanation sentence when present" can't find the text (StockCard doesn't render it yet).

- [ ] **Step 3: Render the explanation in `StockCard.tsx`**

In `frontend/src/components/StockCard.tsx`, change the end of the component from:

```tsx
      ) : (
        <p className="mt-4 text-xs text-ink-400">{stock.excluded_reason}</p>
      )}
    </Card>
  );
}
```

to:

```tsx
      ) : (
        <p className="mt-4 text-xs text-ink-400">{stock.excluded_reason}</p>
      )}

      {stock.explanation && (
        <p className="mt-3 text-xs text-ink-500 dark:text-ink-300">{stock.explanation}</p>
      )}
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- StockCard`
Expected: PASS (5 tests total)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StockCard.tsx frontend/src/components/StockCard.test.tsx
git commit -m "feat: render explanation one-liner on StockCard"
```

---

### Task 4: Split the homepage into Best Today / Long-Term Picks / Short-Term Picks

**Files:**
- Modify: `frontend/src/components/Home.tsx`
- Modify: `frontend/src/components/Home.test.tsx` (full rewrite of the test bodies)

- [ ] **Step 1: Replace `Home.test.tsx` with the category-section tests**

Replace the entire contents of `frontend/src/components/Home.test.tsx` with:

```tsx
import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";
import { Home } from "./Home";
import type { StockSummary } from "../api/client";

function stock(overrides: Partial<StockSummary>): StockSummary {
  return {
    ticker: "TCS.NS",
    name: "Tata Consultancy Services",
    long_term_label: null,
    short_term_label: null,
    long_term_score: null,
    short_term_score: null,
    computed_at: "2026-08-31T18:00:00Z",
    explanation: null,
    excluded_reason: null,
    ...overrides,
  };
}

const bestViaLongTerm = stock({
  ticker: "INFY.NS",
  name: "Infosys",
  long_term_label: "Strong Buy",
  long_term_score: 91.2,
});

const bestViaShortTerm = stock({
  ticker: "TATAMOTORS.NS",
  name: "Tata Motors",
  short_term_label: "Buy",
  short_term_score: 82.0,
});

const bestInBothSections = stock({
  ticker: "HDFCBANK.NS",
  name: "HDFC Bank",
  long_term_label: "Buy",
  long_term_score: 78.4,
  short_term_label: "Strong Buy",
  short_term_score: 88.0,
});

const holdLongTermOnly = stock({
  ticker: "ITC.NS",
  name: "ITC Limited",
  long_term_label: "Hold",
  long_term_score: 60.0,
});

const excluded = stock({
  ticker: "RELIANCE.NS",
  name: "Reliance Industries",
  excluded_reason: "missing required fundamental fields: sector_pe, return_on_equity",
});

test("shows the real universe count, not a hardcoded number", () => {
  render(<Home stocks={[bestViaLongTerm, excluded]} onSelectTicker={vi.fn()} />);
  expect(
    screen.getByText("Screened from our tracked universe of 2 Indian stocks.")
  ).toBeInTheDocument();
});

test("Best Today: only Buy/Strong Buy stocks qualify, ranked by the qualifying score", () => {
  render(
    <Home
      stocks={[bestViaLongTerm, bestViaShortTerm, bestInBothSections, holdLongTermOnly]}
      onSelectTicker={vi.fn()}
    />
  );
  const section = within(screen.getByRole("region", { name: "Best Today" }));
  expect(section.queryByText("ITC Limited")).not.toBeInTheDocument();
  const tickers = section.getAllByText(/\.NS$/).map((el) => el.textContent);
  expect(tickers).toEqual(["INFY.NS", "HDFCBANK.NS", "TATAMOTORS.NS"]);
});

test("Best Today: shows an empty state when nothing qualifies", () => {
  render(<Home stocks={[holdLongTermOnly, excluded]} onSelectTicker={vi.fn()} />);
  const section = within(screen.getByRole("region", { name: "Best Today" }));
  expect(
    section.getByText("No strong opportunity today — check back after the next scoring run.")
  ).toBeInTheDocument();
});

test("Long-Term Picks: includes any non-null long-term label, ranked by long-term score", () => {
  render(
    <Home stocks={[bestViaLongTerm, holdLongTermOnly, bestViaShortTerm]} onSelectTicker={vi.fn()} />
  );
  const section = within(screen.getByRole("region", { name: "Long-Term Picks" }));
  expect(section.queryByText("Tata Motors")).not.toBeInTheDocument();
  const tickers = section.getAllByText(/\.NS$/).map((el) => el.textContent);
  expect(tickers).toEqual(["INFY.NS", "ITC.NS"]);
});

test("Long-Term Picks: shows an empty state when no stock has a long-term label", () => {
  render(<Home stocks={[bestViaShortTerm, excluded]} onSelectTicker={vi.fn()} />);
  const section = within(screen.getByRole("region", { name: "Long-Term Picks" }));
  expect(
    section.getByText("No long-term opportunities right now. Check back after the next scoring run.")
  ).toBeInTheDocument();
});

test("Short-Term Picks: includes any non-null short-term label, ranked by short-term score", () => {
  render(
    <Home stocks={[bestInBothSections, bestViaShortTerm, holdLongTermOnly]} onSelectTicker={vi.fn()} />
  );
  const section = within(screen.getByRole("region", { name: "Short-Term Picks" }));
  expect(section.queryByText("ITC Limited")).not.toBeInTheDocument();
  const tickers = section.getAllByText(/\.NS$/).map((el) => el.textContent);
  expect(tickers).toEqual(["HDFCBANK.NS", "TATAMOTORS.NS"]);
});

test("Short-Term Picks: shows an empty state when no stock has a short-term label", () => {
  render(<Home stocks={[bestViaLongTerm, excluded]} onSelectTicker={vi.fn()} />);
  const section = within(screen.getByRole("region", { name: "Short-Term Picks" }));
  expect(
    section.getByText("No short-term opportunities right now. Check back after the next scoring run.")
  ).toBeInTheDocument();
});

test("a stock can appear in multiple sections at once", () => {
  render(<Home stocks={[bestInBothSections]} onSelectTicker={vi.fn()} />);
  expect(
    within(screen.getByRole("region", { name: "Best Today" })).getByText("HDFCBANK.NS")
  ).toBeInTheDocument();
  expect(
    within(screen.getByRole("region", { name: "Long-Term Picks" })).getByText("HDFCBANK.NS")
  ).toBeInTheDocument();
  expect(
    within(screen.getByRole("region", { name: "Short-Term Picks" })).getByText("HDFCBANK.NS")
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- Home`
Expected: FAIL — `Home` still renders a single list; `getByRole("region", { name: "Best Today" })` throws "Unable to find role".

- [ ] **Step 3: Rewrite `Home.tsx` with the 3 category sections**

Replace the entire contents of `frontend/src/components/Home.tsx` with:

```tsx
import { StockCard } from "./StockCard";
import type { StockSummary } from "../api/client";

const BEST_TODAY_LABELS = new Set(["Strong Buy", "Buy"]);

function isLongTermPick(
  stock: StockSummary
): stock is StockSummary & { long_term_score: number } {
  return stock.long_term_label !== null && stock.long_term_score !== null;
}

function isShortTermPick(
  stock: StockSummary
): stock is StockSummary & { short_term_score: number } {
  return stock.short_term_label !== null && stock.short_term_score !== null;
}

function qualifiesForBestToday(stock: StockSummary): boolean {
  const longQualifies =
    stock.long_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.long_term_label) &&
    stock.long_term_score !== null;
  const shortQualifies =
    stock.short_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.short_term_label) &&
    stock.short_term_score !== null;
  return longQualifies || shortQualifies;
}

function bestTodayRank(stock: StockSummary): number {
  const longRank =
    stock.long_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.long_term_label) &&
    stock.long_term_score !== null
      ? stock.long_term_score
      : Number.NEGATIVE_INFINITY;
  const shortRank =
    stock.short_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.short_term_label) &&
    stock.short_term_score !== null
      ? stock.short_term_score
      : Number.NEGATIVE_INFINITY;
  return Math.max(longRank, shortRank);
}

function CategorySection({
  title,
  emptyMessage,
  stocks,
  onSelectTicker,
}: {
  title: string;
  emptyMessage: string;
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  return (
    <section aria-label={title} className="mt-8 first:mt-6">
      <h3 className="text-lg font-semibold text-ink-900 dark:text-white">{title}</h3>
      {stocks.length === 0 ? (
        <p className="mt-4 text-sm text-ink-400">{emptyMessage}</p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {stocks.map((stock) => (
            <StockCard key={stock.ticker} stock={stock} onSelect={onSelectTicker} />
          ))}
        </div>
      )}
    </section>
  );
}

export function Home({
  stocks,
  onSelectTicker,
}: {
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  const bestToday = stocks
    .filter(qualifiesForBestToday)
    .sort((a, b) => bestTodayRank(b) - bestTodayRank(a));

  const longTermPicks = stocks
    .filter(isLongTermPick)
    .sort((a, b) => b.long_term_score - a.long_term_score);

  const shortTermPicks = stocks
    .filter(isShortTermPick)
    .sort((a, b) => b.short_term_score - a.short_term_score);

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">
        AI Picks Today
      </h2>
      <p className="mt-1 text-sm text-ink-400">
        Screened from our tracked universe of {stocks.length} Indian stocks.
      </p>

      <CategorySection
        title="Best Today"
        emptyMessage="No strong opportunity today — check back after the next scoring run."
        stocks={bestToday}
        onSelectTicker={onSelectTicker}
      />
      <CategorySection
        title="Long-Term Picks"
        emptyMessage="No long-term opportunities right now. Check back after the next scoring run."
        stocks={longTermPicks}
        onSelectTicker={onSelectTicker}
      />
      <CategorySection
        title="Short-Term Picks"
        emptyMessage="No short-term opportunities right now. Check back after the next scoring run."
        stocks={shortTermPicks}
        onSelectTicker={onSelectTicker}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- Home`
Expected: PASS (9 tests total)

- [ ] **Step 5: Run the full frontend suite and type check**

Run: `cd frontend && npx tsc --noEmit && npm test`
Expected: all test files pass, no type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Home.tsx frontend/src/components/Home.test.tsx
git commit -m "feat: split homepage into Best Today / Long-Term / Short-Term categories"
```

---

### Task 5: Final cross-module check

**Files:** none modified — verification only.

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend && python3 -m pytest -v`
Expected: all tests pass, no regressions outside `test_routes.py`.

- [ ] **Step 2: Run the full frontend suite and build**

Run: `cd frontend && npm test && npm run build`
Expected: all tests pass; `npm run build` succeeds (runs `tsc` then `vite build`); check `dist/assets/*.css` is non-trivial in size (not 0.06kB — this repo has a known history of empty-Tailwind-build regressions), per DECISIONS.md 2026-08-31 note.

- [ ] **Step 3: Manually verify in the browser**

Run: `cd backend && uvicorn app.api.main:app --reload` (one terminal) and `cd frontend && npm run dev` (another terminal). Open the dev URL, confirm the homepage shows 3 sections with correct empty/populated states against real seeded data, and cards show the one-liner explanation.
