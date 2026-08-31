# Consumer UX Redesign — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the existing Fintrixa frontend into the two-nav (Home/Discover), card-based, progressive-disclosure IA from `docs/superpowers/specs/2026-08-31-consumer-ux-phase-a-design.md`, using only fields the backend already returns — no fabricated confidence/holding-period/forecast data.

**Architecture:** Frontend-only change, `frontend/src/` — no backend, no scoring-formula touch (backtest gate does not apply). New `StockCard` component replaces table rows; `Home`/`Discover` replace the single ranked-list view; `StockDetail` gets a collapsed-by-default "Show details" section; `VerdictBadge` gets a display-label mapping layer. `RankedTable` is fully superseded and deleted.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind v4, vitest + @testing-library/react + @testing-library/user-event.

---

### Task 1: Verdict display-label mapping

**Files:**
- Create: `frontend/src/lib/verdictDisplay.ts`
- Test: `frontend/src/lib/verdictDisplay.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { expect, test } from "vitest";
import { toDisplayLabel } from "./verdictDisplay";

test("maps each backend verdict label to consumer-friendly text", () => {
  expect(toDisplayLabel("Strong Buy")).toBe("Strong Opportunity");
  expect(toDisplayLabel("Buy")).toBe("Potential Opportunity");
  expect(toDisplayLabel("Hold")).toBe("Worth Watching");
  expect(toDisplayLabel("Avoid")).toBe("No Clear Opportunity");
});

test("falls back to the raw label for an unrecognized value", () => {
  expect(toDisplayLabel("Mystery")).toBe("Mystery");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/verdictDisplay.test.ts`
Expected: FAIL — `Failed to resolve import "./verdictDisplay"`

- [ ] **Step 3: Write minimal implementation**

```ts
const DISPLAY_LABELS: Record<string, string> = {
  "Strong Buy": "Strong Opportunity",
  Buy: "Potential Opportunity",
  Hold: "Worth Watching",
  Avoid: "No Clear Opportunity",
};

export function toDisplayLabel(label: string): string {
  return DISPLAY_LABELS[label] ?? label;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/verdictDisplay.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/verdictDisplay.ts frontend/src/lib/verdictDisplay.test.ts
git commit -m "feat: add consumer-friendly verdict label mapping"
```

---

### Task 2: Wire the display mapping into VerdictBadge

**Files:**
- Modify: `frontend/src/components/VerdictBadge.tsx`
- Test: `frontend/src/components/VerdictBadge.test.tsx` (new)

**Context:** `VerdictBadge` currently renders the raw backend label (`"Buy"`) as both the color-variant key and the visible text. It must keep using the raw label for the variant/color lookup (that logic is correct and untouched) but render the softened label as the visible text, so every existing caller (`StockDetail`, and the new `StockCard`) gets the change for free.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { VerdictBadge } from "./VerdictBadge";

test("renders the consumer-friendly label, not the raw backend label", () => {
  render(<VerdictBadge label="Buy" />);
  expect(screen.getByText("Potential Opportunity")).toBeInTheDocument();
  expect(screen.queryByText("Buy")).not.toBeInTheDocument();
});

test("falls back to the raw label for an unrecognized value", () => {
  render(<VerdictBadge label="Mystery" />);
  expect(screen.getByText("Mystery")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/VerdictBadge.test.tsx`
Expected: FAIL — expected element with text `Potential Opportunity` not found (current render shows `Buy`)

- [ ] **Step 3: Write minimal implementation**

Replace the full contents of `frontend/src/components/VerdictBadge.tsx`:

```tsx
import { Badge } from "./ui/badge";
import { toDisplayLabel } from "../lib/verdictDisplay";

const VARIANT_MAP: Record<string, "strong-buy" | "buy" | "hold" | "avoid"> = {
  "Strong Buy": "strong-buy",
  Buy: "buy",
  Hold: "hold",
  Avoid: "avoid",
};

export function VerdictBadge({ label }: { label: string }) {
  return <Badge variant={VARIANT_MAP[label] ?? "neutral"}>{toDisplayLabel(label)}</Badge>;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/VerdictBadge.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full suite to check for regressions from the label change**

Run: `cd frontend && npm test -- --run`
Expected: `RankedTable.test.tsx` FAILS — it asserts `screen.getByText("Buy")`, which no longer renders. This is expected; Task 5 deletes `RankedTable` entirely. Confirm no other test file fails.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/VerdictBadge.tsx frontend/src/components/VerdictBadge.test.tsx
git commit -m "feat: show consumer-friendly verdict text in VerdictBadge"
```

---

### Task 3: StockCard component

**Files:**
- Create: `frontend/src/components/StockCard.tsx`
- Test: `frontend/src/components/StockCard.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { StockCard } from "./StockCard";
import type { StockSummary } from "../api/client";

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

test("renders name, ticker, softened verdict labels, and each score", () => {
  render(<StockCard stock={stock} onSelect={vi.fn()} />);
  expect(screen.getByText("TCS.NS")).toBeInTheDocument();
  expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument();
  expect(screen.getByText("Potential Opportunity")).toBeInTheDocument();
  expect(screen.getByText("Worth Watching")).toBeInTheDocument();
  expect(screen.getByText("78/100")).toBeInTheDocument();
  expect(screen.getByText("55/100")).toBeInTheDocument();
});

test("renders the excluded reason instead of badges when there is no verdict", () => {
  const excluded: StockSummary = {
    ...stock,
    long_term_label: null,
    short_term_label: null,
    excluded_reason: "missing required fundamental fields: sector_pe",
  };
  render(<StockCard stock={excluded} onSelect={vi.fn()} />);
  expect(screen.getByText("missing required fundamental fields: sector_pe")).toBeInTheDocument();
});

test("calls onSelect with the ticker when clicked", async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  render(<StockCard stock={stock} onSelect={onSelect} />);
  await user.click(screen.getByText("TCS.NS"));
  expect(onSelect).toHaveBeenCalledWith("TCS.NS");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/StockCard.test.tsx`
Expected: FAIL — `Failed to resolve import "./StockCard"`

- [ ] **Step 3: Write minimal implementation**

```tsx
import type { KeyboardEvent } from "react";
import { VerdictBadge } from "./VerdictBadge";
import { Card } from "./ui/card";
import type { StockSummary } from "../api/client";

export function StockCard({
  stock,
  onSelect,
}: {
  stock: StockSummary;
  onSelect: (ticker: string) => void;
}) {
  const hasVerdict = stock.long_term_label !== null || stock.short_term_label !== null;

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(stock.ticker);
    }
  }

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => onSelect(stock.ticker)}
      onKeyDown={handleKeyDown}
      className="cursor-pointer p-5 transition hover:border-lavender-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:hover:border-lavender-500/40"
    >
      <div className="text-base font-semibold text-ink-900 dark:text-white">{stock.name}</div>
      <div className="font-mono text-xs text-ink-400">{stock.ticker}</div>

      {hasVerdict ? (
        <div className="mt-4 flex flex-wrap gap-4">
          {stock.long_term_label && (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-ink-400">Long-term</div>
              <VerdictBadge label={stock.long_term_label} />
              {stock.long_term_score !== null && (
                <div className="mt-1 text-xs text-ink-400">
                  {Math.round(stock.long_term_score)}/100
                </div>
              )}
            </div>
          )}
          {stock.short_term_label && (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-ink-400">Short-term</div>
              <VerdictBadge label={stock.short_term_label} />
              {stock.short_term_score !== null && (
                <div className="mt-1 text-xs text-ink-400">
                  {Math.round(stock.short_term_score)}/100
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <p className="mt-4 text-xs text-ink-400">{stock.excluded_reason}</p>
      )}
    </Card>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/StockCard.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StockCard.tsx frontend/src/components/StockCard.test.tsx
git commit -m "feat: add StockCard replacing table rows with the consumer card layout"
```

---

### Task 4: Home view ("AI Picks Today")

**Files:**
- Create: `frontend/src/components/Home.tsx`
- Test: `frontend/src/components/Home.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { Home } from "./Home";
import type { StockSummary } from "../api/client";

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

const excluded: StockSummary = {
  ticker: "RELIANCE.NS",
  name: "Reliance Industries",
  long_term_label: null,
  short_term_label: null,
  long_term_score: null,
  short_term_score: null,
  computed_at: null,
  excluded_reason: "missing required fundamental fields: sector_pe, return_on_equity",
};

test("shows the real universe count, not a hardcoded number", () => {
  render(<Home stocks={[scored, excluded]} onSelectTicker={vi.fn()} />);
  expect(
    screen.getByText("Screened from our tracked universe of 2 Indian stocks.")
  ).toBeInTheDocument();
});

test("only lists stocks that have a verdict", () => {
  render(<Home stocks={[scored, excluded]} onSelectTicker={vi.fn()} />);
  expect(screen.getByText("TCS.NS")).toBeInTheDocument();
  expect(screen.queryByText("RELIANCE.NS")).not.toBeInTheDocument();
});

test("shows an empty state when no stock has a verdict", () => {
  render(<Home stocks={[excluded]} onSelectTicker={vi.fn()} />);
  expect(
    screen.getByText("No strong opportunities right now. Check back after the next scoring run.")
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/Home.test.tsx`
Expected: FAIL — `Failed to resolve import "./Home"`

- [ ] **Step 3: Write minimal implementation**

```tsx
import { StockCard } from "./StockCard";
import type { StockSummary } from "../api/client";

export function Home({
  stocks,
  onSelectTicker,
}: {
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  const ranked = stocks
    .filter((stock) => stock.long_term_label !== null || stock.short_term_label !== null)
    .sort(
      (a, b) =>
        (b.long_term_score ?? b.short_term_score ?? 0) -
        (a.long_term_score ?? a.short_term_score ?? 0)
    );

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">
        AI Picks Today
      </h2>
      <p className="mt-1 text-sm text-ink-400">
        Screened from our tracked universe of {stocks.length} Indian stocks.
      </p>

      {ranked.length === 0 ? (
        <p className="mt-8 text-sm text-ink-400">
          No strong opportunities right now. Check back after the next scoring run.
        </p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {ranked.map((stock) => (
            <StockCard key={stock.ticker} stock={stock} onSelect={onSelectTicker} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/Home.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Home.tsx frontend/src/components/Home.test.tsx
git commit -m "feat: add Home view showing today's ranked AI picks"
```

---

### Task 5: Discover view, retiring RankedTable

**Files:**
- Create: `frontend/src/components/Discover.tsx`
- Test: `frontend/src/components/Discover.test.tsx`
- Delete: `frontend/src/components/RankedTable.tsx`
- Delete: `frontend/src/components/RankedTable.test.tsx`

**Context:** `Discover` is the "see everything" view — every stock, scored or not, fully superseding what `RankedTable` did as a table. Nothing else imports `RankedTable` after Task 6 rewires `App.tsx`, so it becomes dead code; delete it now rather than leaving an unused component behind.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { Discover } from "./Discover";
import type { StockSummary } from "../api/client";

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

test("renders every stock including ones with no verdict", () => {
  render(<Discover stocks={stocks} onSelectTicker={vi.fn()} />);
  expect(screen.getByText("RELIANCE.NS")).toBeInTheDocument();
  expect(
    screen.getByText("missing required fundamental fields: sector_pe, return_on_equity")
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/Discover.test.tsx`
Expected: FAIL — `Failed to resolve import "./Discover"`

- [ ] **Step 3: Write minimal implementation**

```tsx
import { StockCard } from "./StockCard";
import type { StockSummary } from "../api/client";

export function Discover({
  stocks,
  onSelectTicker,
}: {
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">Discover</h2>
      <p className="mt-1 text-sm text-ink-400">
        Every stock in our tracked universe, scored or not.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {stocks.map((stock) => (
          <StockCard key={stock.ticker} stock={stock} onSelect={onSelectTicker} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/Discover.test.tsx`
Expected: PASS (1 test)

- [ ] **Step 5: Delete the superseded RankedTable component and its test**

```bash
rm frontend/src/components/RankedTable.tsx frontend/src/components/RankedTable.test.tsx
```

- [ ] **Step 6: Commit**

```bash
git add -A frontend/src/components/Discover.tsx frontend/src/components/Discover.test.tsx \
  frontend/src/components/RankedTable.tsx frontend/src/components/RankedTable.test.tsx
git commit -m "feat: add Discover view, remove superseded RankedTable"
```

Note: `App.tsx` still imports `RankedTable` at this point, so `npm run build` / `npm test` will fail until Task 6 rewires it. That's expected — proceed directly to Task 6.

---

### Task 6: Progressive disclosure on the stock detail page

**Files:**
- Modify: `frontend/src/components/StockDetail.tsx`
- Modify: `frontend/src/components/StockDetail.test.tsx`

**Context:** The "Score breakdown" card (fundamental/technical sub-scores + weighting note) is Level 2 detail per the design spec — collapsed by default, revealed by a "Show details" toggle. The "Suggested action" card and price chart stay visible by default (Level 1).

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/components/StockDetail.test.tsx` (add `import userEvent from "@testing-library/user-event";` to the top imports alongside the existing ones):

```tsx
test("score breakdown is hidden by default and shown after clicking Show details", async () => {
  const user = userEvent.setup();
  render(
    <StockDetail
      detail={baseDetail}
      detailError={null}
      history={[]}
      historyError={null}
      onBack={vi.fn()}
    />
  );

  expect(screen.queryByText("Score breakdown")).not.toBeInTheDocument();

  await user.click(screen.getByText("Show details"));

  expect(screen.getByText("Score breakdown")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/StockDetail.test.tsx`
Expected: FAIL — `Score breakdown` card is currently always rendered, and no "Show details" text exists yet, so `getByText("Show details")` throws

- [ ] **Step 3: Write minimal implementation**

In `frontend/src/components/StockDetail.tsx`:

1. Add `useState` to the React import (line 1 currently has no import from `"react"` — add one):

```tsx
import { useState } from "react";
```

2. Inside the `StockDetail` function, add the state hook as the first line of the function body (before the `if (detailError)` early return, so hook order stays stable):

```tsx
export function StockDetail({
  detail,
  detailError,
  history,
  historyError,
  onBack,
}: {
  detail: StockDetailData | null;
  detailError: string | null;
  history: PriceHistoryPoint[] | null;
  historyError: string | null;
  onBack: () => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  if (detailError) {
```

3. Replace the existing always-rendered "Score breakdown" `<Card>` block with a toggle button plus a conditionally rendered card:

```tsx
      <button
        type="button"
        onClick={() => setShowDetails((value) => !value)}
        className="mb-6 inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-lavender-700 hover:bg-lavender-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:text-lavender-300 dark:hover:bg-lavender-900/20"
      >
        {showDetails ? "Hide details" : "Show details"}
      </button>

      {showDetails && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Score breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <ScoreTile label="Fundamental" score={detail.fundamental_score} />
              <ScoreTile label="Technical" score={detail.technical_score} />
            </div>
            <p className="mt-3 text-xs text-ink-400">
              Long-term verdict weights fundamentals 70% / technicals 30%. Short-term verdict
              weights technicals 70% / fundamentals 30%.
            </p>
          </CardContent>
        </Card>
      )}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/StockDetail.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StockDetail.tsx frontend/src/components/StockDetail.test.tsx
git commit -m "feat: collapse score breakdown behind a Show details toggle"
```

---

### Task 7: Wire Home/Discover navigation into App

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, beforeEach } from "vitest";
import { App } from "./App";
import * as client from "./api/client";
import type { StockSummary } from "./api/client";

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

beforeEach(() => {
  vi.spyOn(client, "fetchStocks").mockResolvedValue(stocks);
});

test("defaults to the Home view", async () => {
  render(<App />);
  expect(await screen.findByText("AI Picks Today")).toBeInTheDocument();
});

test("switching to Discover shows every tracked stock", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("AI Picks Today");

  await user.click(screen.getByRole("button", { name: "Discover" }));

  expect(
    await screen.findByText("Every stock in our tracked universe, scored or not.")
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: FAIL — `App` currently renders the old "Ranked stocks" card, not "AI Picks Today"; also `App.tsx` still imports the deleted `RankedTable`, so this will fail at import/build time first

- [ ] **Step 3: Write minimal implementation**

Replace the full contents of `frontend/src/App.tsx`:

```tsx
import { useEffect, useState } from "react";
import {
  fetchStockDetail,
  fetchStockHistory,
  fetchStocks,
  type PriceHistoryPoint,
  type StockDetail as StockDetailData,
  type StockSummary,
} from "./api/client";
import { Home } from "./components/Home";
import { Discover } from "./components/Discover";
import { StockDetail } from "./components/StockDetail";
import { Skeleton } from "./components/ui/skeleton";
import { Alert } from "./components/ui/alert";

type View = "home" | "discover";

export function App() {
  const [view, setView] = useState<View>("home");
  const [stocks, setStocks] = useState<StockSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [detail, setDetail] = useState<StockDetailData | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [history, setHistory] = useState<PriceHistoryPoint[] | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  useEffect(() => {
    fetchStocks()
      .then(setStocks)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedTicker) return;

    setDetail(null);
    setDetailError(null);
    setHistory(null);
    setHistoryError(null);

    fetchStockDetail(selectedTicker)
      .then(setDetail)
      .catch((err) => setDetailError(err.message));

    fetchStockHistory(selectedTicker)
      .then(setHistory)
      .catch((err) => setHistoryError(err.message));
  }, [selectedTicker]);

  function navButtonClass(active: boolean) {
    return active
      ? "rounded-md bg-lavender-100 px-3 py-1.5 text-sm font-semibold text-lavender-700 dark:bg-lavender-900/40 dark:text-lavender-300"
      : "rounded-md px-3 py-1.5 text-sm font-medium text-ink-400 hover:text-ink-900 dark:hover:text-white";
  }

  return (
    <div className="min-h-screen bg-off-white text-ink-900 dark:bg-black dark:text-white">
      <header className="border-b border-lavender-100 bg-white/80 backdrop-blur dark:border-lavender-900/40 dark:bg-black/80">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-bold tracking-tight text-lavender-700 dark:text-lavender-300">
            Fintrixa
          </h1>
          <nav className="flex gap-1">
            <button
              type="button"
              className={navButtonClass(view === "home")}
              onClick={() => {
                setSelectedTicker(null);
                setView("home");
              }}
            >
              Home
            </button>
            <button
              type="button"
              className={navButtonClass(view === "discover")}
              onClick={() => {
                setSelectedTicker(null);
                setView("discover");
              }}
            >
              Discover
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {selectedTicker ? (
          <StockDetail
            detail={detail}
            detailError={detailError}
            history={history}
            historyError={historyError}
            onBack={() => setSelectedTicker(null)}
          />
        ) : (
          <>
            {error && <Alert>{error}</Alert>}
            {!error && !stocks && (
              <div className="space-y-2">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            )}
            {stocks && view === "home" && (
              <Home stocks={stocks} onSelectTicker={setSelectedTicker} />
            )}
            {stocks && view === "discover" && (
              <Discover stocks={stocks} onSelectTicker={setSelectedTicker} />
            )}
          </>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: wire Home/Discover navigation into App"
```

---

### Task 8: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd frontend && npm test -- --run`
Expected: All test files pass — `verdictDisplay.test.ts`, `VerdictBadge.test.tsx`, `StockCard.test.tsx`, `Home.test.tsx`, `Discover.test.tsx`, `StockDetail.test.tsx`, `App.test.tsx`. No reference to `RankedTable` remains anywhere (`grep -rn RankedTable frontend/src` returns nothing).

- [ ] **Step 2: Run the production build and confirm real CSS output**

Run: `cd frontend && npm run build`
Expected: Build succeeds. Then run `ls -la dist/assets/*.css` and confirm the file is several KB (not near-zero) — per `docs/DECISIONS.md`, a passing build does not by itself prove Tailwind actually generated styles.

- [ ] **Step 3: Visually verify against live data**

Start (or confirm running) the backend on port 8000 and the frontend dev server on port 5173. Load `http://localhost:5173` and confirm, against real seeded data:
- Home shows "AI Picks Today" with the real universe count and cards only for stocks with a verdict (e.g. TCS.NS, INFY.NS from the seeded universe).
- Clicking "Discover" in the nav shows every seeded stock, including ones with an `excluded_reason` (e.g. RELIANCE.NS).
- Clicking a scored stock's card opens its detail page: verdict badges show softened text (e.g. "Potential Opportunity", not "Buy"), the "Suggested action" card and price chart are visible immediately, and the "Score breakdown" card is hidden until "Show details" is clicked.
- No console errors in the browser.

Take a screenshot of each of the three states (Home, Discover, a stock detail page with details expanded) as evidence.

- [ ] **Step 4: Commit any fixes found during verification**

If Step 3 surfaces a real defect, fix it, re-run Steps 1–3, then commit:

```bash
git add -A
git commit -m "fix: <describe what verification caught>"
```

If nothing needed fixing, no commit is required for this task.
