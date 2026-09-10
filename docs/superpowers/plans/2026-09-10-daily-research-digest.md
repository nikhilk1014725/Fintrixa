# Daily Research Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Research" screen showing every stock the daily news-research job has ever researched, grouped by day, with a confidence badge and red-flag count at a glance — filterable by date, defaulting to the most recent day.

**Architecture:** One new read-only backend endpoint joins the existing `NewsCorroboration` and `Stock` tables (no schema change — the data already exists), returning every row sorted newest-first. The frontend groups those rows by calendar date client-side, dedupes same-day duplicates per stock (keeping the latest), and renders a date-picker + list, reusing the existing `Card`/`Badge` primitives and the same click-through-to-detail wiring already used by `Home`/`Discover`/`Holdings`.

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic (backend), React + TypeScript + Vitest/RTL (frontend).

Spec: `docs/superpowers/specs/2026-09-10-daily-research-digest-design.md`

---

### Task 1: `GET /news-digest` endpoint

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_news_digest_routes.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_news_digest_routes.py`:

```python
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.db import Base, get_db
from app.models import NewsCorroboration, Stock


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    db = TestSession()
    stock_a = Stock(ticker="TCS.NS", name="Tata Consultancy Services")
    stock_b = Stock(ticker="RELIANCE.NS", name="Reliance Industries")
    stock_c = Stock(ticker="INFY.NS", name="Infosys")
    db.add_all([stock_a, stock_b, stock_c])
    db.flush()

    db.add(
        NewsCorroboration(
            stock_id=stock_a.id,
            computed_at=datetime(2026, 9, 9, 8, 0, 0),
            bull_case="bull",
            bear_case="bear",
            red_flags=["old flag"],
            confidence="Mixed",
            sources=[],
        )
    )
    db.add(
        NewsCorroboration(
            stock_id=stock_a.id,
            computed_at=datetime(2026, 9, 10, 8, 0, 0),
            bull_case="bull",
            bear_case="bear",
            red_flags=[],
            confidence="Corroborated",
            sources=[],
        )
    )
    db.add(
        NewsCorroboration(
            stock_id=stock_b.id,
            computed_at=datetime(2026, 9, 10, 8, 5, 0),
            bull_case="bull",
            bear_case="bear",
            red_flags=["flag one", "flag two"],
            confidence="Mixed",
            sources=[],
        )
    )
    # stock_c has no NewsCorroboration row at all -- must not appear
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            db.rollback()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db.close()


def test_news_digest_returns_rows_sorted_by_computed_at_desc(client):
    response = client.get("/news-digest")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    tickers_in_order = [row["ticker"] for row in body]
    assert tickers_in_order == ["RELIANCE.NS", "TCS.NS", "TCS.NS"]


def test_news_digest_includes_red_flag_count(client):
    response = client.get("/news-digest")
    body = response.json()
    reliance_row = next(r for r in body if r["ticker"] == "RELIANCE.NS")
    assert reliance_row["red_flag_count"] == 2
    assert reliance_row["confidence"] == "Mixed"


def test_news_digest_zero_red_flags_returns_zero_count(client):
    response = client.get("/news-digest")
    body = response.json()
    latest_tcs_row = next(
        r for r in body if r["ticker"] == "TCS.NS" and r["computed_at"].startswith("2026-09-10")
    )
    assert latest_tcs_row["red_flag_count"] == 0


def test_news_digest_excludes_stocks_with_no_corroboration(client):
    response = client.get("/news-digest")
    body = response.json()
    tickers = {row["ticker"] for row in body}
    assert "INFY.NS" not in tickers
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_digest_routes.py -v`
Expected: FAIL — `/news-digest` returns 404 (route doesn't exist yet).

- [ ] **Step 3: Add the `NewsDigestEntry` schema**

Append to the end of `backend/app/schemas.py`:

```python
class NewsDigestEntry(BaseModel):
    ticker: str
    name: str
    computed_at: datetime
    confidence: str
    red_flag_count: int
```

- [ ] **Step 4: Add the endpoint**

At the top of `backend/app/api/routes.py`, change:

```python
from app.schemas import HoldingCreate, HoldingGrading, HoldingResponse, PriceHistoryPoint, StockDetail, StockSummary
```

to:

```python
from app.schemas import (
    HoldingCreate,
    HoldingGrading,
    HoldingResponse,
    NewsDigestEntry,
    PriceHistoryPoint,
    StockDetail,
    StockSummary,
)
```

Then append to the end of the file:

```python
@router.get("/news-digest", response_model=list[NewsDigestEntry])
def news_digest(db: Session = Depends(get_db)):
    stmt = (
        select(NewsCorroboration, Stock.ticker, Stock.name)
        .join(Stock, NewsCorroboration.stock_id == Stock.id)
        .order_by(NewsCorroboration.computed_at.desc())
    )
    rows = db.execute(stmt).all()
    return [
        NewsDigestEntry(
            ticker=ticker,
            name=name,
            computed_at=corroboration.computed_at,
            confidence=corroboration.confidence,
            red_flag_count=len(corroboration.red_flags),
        )
        for corroboration, ticker, name in rows
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_news_digest_routes.py -v`
Expected: `4 passed`

Then run the full backend suite to confirm no regressions: `cd backend && .venv/bin/python -m pytest -v`
Expected: all tests pass, zero failures.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/api/routes.py backend/tests/test_news_digest_routes.py
git commit -m "feat: add GET /news-digest endpoint"
```

---

### Task 2: Frontend API client

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add the type and function**

Append to the end of `frontend/src/api/client.ts`:

```ts
export interface NewsDigestEntry {
  ticker: string;
  name: string;
  computed_at: string;
  confidence: string;
  red_flag_count: number;
}

export async function fetchNewsDigest(): Promise<NewsDigestEntry[]> {
  const response = await fetch(`${API_BASE}/news-digest`);
  if (!response.ok) {
    throw new Error(`failed to fetch news digest: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no output (success).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add news digest API client function"
```

---

### Task 3: `ResearchDigest` component

**Files:**
- Create: `frontend/src/components/ResearchDigest.tsx`
- Test: `frontend/src/components/ResearchDigest.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/ResearchDigest.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ResearchDigest } from "./ResearchDigest";
import type { NewsDigestEntry } from "../api/client";

const entries: NewsDigestEntry[] = [
  {
    ticker: "RELIANCE.NS",
    name: "Reliance Industries",
    computed_at: "2026-09-10T08:05:00Z",
    confidence: "Mixed",
    red_flag_count: 2,
  },
  {
    ticker: "TCS.NS",
    name: "Tata Consultancy Services",
    computed_at: "2026-09-10T08:00:00Z",
    confidence: "Corroborated",
    red_flag_count: 0,
  },
  {
    ticker: "TCS.NS",
    name: "Tata Consultancy Services",
    computed_at: "2026-09-09T08:00:00Z",
    confidence: "Mixed",
    red_flag_count: 1,
  },
];

test("shows an empty state when there is no research at all", () => {
  render(<ResearchDigest entries={[]} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getByText("No research has been logged yet.")).toBeInTheDocument();
});

test("defaults to the most recent date and shows its stocks", () => {
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getByRole("combobox")).toHaveValue("2026-09-10");
  expect(screen.getByText("Reliance Industries")).toBeInTheDocument();
  expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument();
});

test("shows the red-flag count badge only when there are red flags", () => {
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getByText("2 red flags")).toBeInTheDocument();
  expect(screen.queryByText(/0 red flag/)).not.toBeInTheDocument();
});

test("switching the date dropdown shows that day's stocks instead", async () => {
  const user = userEvent.setup();
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={vi.fn()} />);

  await user.selectOptions(screen.getByRole("combobox"), "2026-09-09");

  expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument();
  expect(screen.queryByText("Reliance Industries")).not.toBeInTheDocument();
  expect(screen.getByText("1 red flag")).toBeInTheDocument();
});

test("collapses duplicate same-day entries for a stock, keeping the latest", () => {
  const sameDayDuplicate: NewsDigestEntry[] = [
    {
      ticker: "TCS.NS",
      name: "Tata Consultancy Services",
      computed_at: "2026-09-10T08:05:00Z",
      confidence: "Corroborated",
      red_flag_count: 0,
    },
    {
      ticker: "TCS.NS",
      name: "Tata Consultancy Services",
      computed_at: "2026-09-10T07:00:00Z",
      confidence: "Mixed",
      red_flag_count: 1,
    },
  ];
  render(<ResearchDigest entries={sameDayDuplicate} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getAllByText("Tata Consultancy Services")).toHaveLength(1);
  expect(screen.getByText("Corroborated")).toBeInTheDocument();
});

test("tapping a row calls onSelectTicker with its ticker", async () => {
  const user = userEvent.setup();
  const onSelectTicker = vi.fn();
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={onSelectTicker} />);
  await user.click(screen.getByText("Reliance Industries"));
  expect(onSelectTicker).toHaveBeenCalledWith("RELIANCE.NS");
});

test("shows an error alert when fetching failed", () => {
  render(
    <ResearchDigest entries={null} error="failed to fetch news digest: 500" onSelectTicker={vi.fn()} />
  );
  expect(screen.getByText("failed to fetch news digest: 500")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run ResearchDigest`
Expected: FAIL — `Cannot find module './ResearchDigest'`

- [ ] **Step 3: Write the component**

Create `frontend/src/components/ResearchDigest.tsx`:

```tsx
import { useMemo, useState, type KeyboardEvent } from "react";
import type { NewsDigestEntry } from "../api/client";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Alert } from "./ui/alert";

function formatDateLabel(dateKey: string): string {
  const d = new Date(`${dateKey}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateKey;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function groupByDate(entries: NewsDigestEntry[]): Map<string, NewsDigestEntry[]> {
  const groups = new Map<string, NewsDigestEntry[]>();
  const seen = new Set<string>();
  for (const entry of entries) {
    const dateKey = entry.computed_at.slice(0, 10);
    const dedupeKey = `${dateKey}|${entry.ticker}`;
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);
    const group = groups.get(dateKey);
    if (group) {
      group.push(entry);
    } else {
      groups.set(dateKey, [entry]);
    }
  }
  return groups;
}

export function ResearchDigest({
  entries,
  error,
  onSelectTicker,
}: {
  entries: NewsDigestEntry[] | null;
  error: string | null;
  onSelectTicker: (ticker: string) => void;
}) {
  const groups = useMemo(() => (entries ? groupByDate(entries) : new Map<string, NewsDigestEntry[]>()), [
    entries,
  ]);
  const dates = useMemo(() => Array.from(groups.keys()).sort().reverse(), [groups]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const activeDate = selectedDate && dates.includes(selectedDate) ? selectedDate : (dates[0] ?? null);
  const rows = activeDate ? (groups.get(activeDate) ?? []) : [];

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">Research Digest</h2>
      <p className="mt-1 text-sm text-ink-400">
        What the daily AI news research found, one day at a time.
      </p>

      {error && <Alert className="mt-4">{error}</Alert>}

      {!error && entries && entries.length === 0 && (
        <p className="mt-8 text-sm text-ink-400">No research has been logged yet.</p>
      )}

      {!error && dates.length > 0 && activeDate && (
        <>
          <label className="mt-6 block text-xs font-medium text-ink-400" htmlFor="digest-date">
            Date
          </label>
          <select
            id="digest-date"
            value={activeDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="mt-1 rounded-md border border-lavender-100 px-2 py-1.5 text-sm dark:border-lavender-900/40 dark:bg-black"
          >
            {dates.map((date) => (
              <option key={date} value={date}>
                {formatDateLabel(date)}
              </option>
            ))}
          </select>

          <div className="mt-4 space-y-3">
            {rows.map((entry) => {
              function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectTicker(entry.ticker);
                }
              }

              return (
                <Card
                  key={entry.ticker}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectTicker(entry.ticker)}
                  onKeyDown={handleKeyDown}
                  className="cursor-pointer p-4 transition hover:border-lavender-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:hover:border-lavender-500/40"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-base font-semibold text-ink-900 dark:text-white">
                        {entry.name}
                      </div>
                      <div className="font-mono text-xs text-ink-400">{entry.ticker}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="neutral">{entry.confidence}</Badge>
                      {entry.red_flag_count > 0 && (
                        <Badge variant="avoid">
                          {entry.red_flag_count} red flag{entry.red_flag_count > 1 ? "s" : ""}
                        </Badge>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --run ResearchDigest`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ResearchDigest.tsx frontend/src/components/ResearchDigest.test.tsx
git commit -m "feat: add Research Digest screen component"
```

---

### Task 4: Wire `ResearchDigest` into `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

First, read the current contents of `frontend/src/App.tsx` and `frontend/src/App.test.tsx` yourself before making changes — the structure below should match, but confirm.

- [ ] **Step 1: Write the failing test**

In `frontend/src/App.test.tsx`, find the existing import line (it currently reads `import type { Holding, StockSummary } from "./api/client";`) and change it to:

```tsx
import type { Holding, NewsDigestEntry, StockSummary } from "./api/client";
```

Then add this test at the end of the file:

```tsx
test("switching to Research shows the research digest screen", async () => {
  const user = userEvent.setup();
  const entries: NewsDigestEntry[] = [];
  vi.spyOn(client, "fetchNewsDigest").mockResolvedValue(entries);

  render(<App />);
  await screen.findByText("AI Picks Today");

  await user.click(screen.getByRole("button", { name: "Research" }));

  expect(await screen.findByText("Research Digest")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run App`
Expected: FAIL — no button named "Research" exists yet.

- [ ] **Step 3: Wire it up in `App.tsx`**

Change the imports at the top of `frontend/src/App.tsx` from:

```tsx
import { useEffect, useState } from "react";
import {
  fetchHoldings,
  fetchStockDetail,
  fetchStockHistory,
  fetchStocks,
  type Holding,
  type PriceHistoryPoint,
  type StockDetail as StockDetailData,
  type StockSummary,
} from "./api/client";
import { Home } from "./components/Home";
import { Discover } from "./components/Discover";
import { Holdings } from "./components/Holdings";
import { StockDetail } from "./components/StockDetail";
import { Skeleton } from "./components/ui/skeleton";
import { Alert } from "./components/ui/alert";

type View = "home" | "discover" | "holdings";
```

to:

```tsx
import { useEffect, useState } from "react";
import {
  fetchHoldings,
  fetchNewsDigest,
  fetchStockDetail,
  fetchStockHistory,
  fetchStocks,
  type Holding,
  type NewsDigestEntry,
  type PriceHistoryPoint,
  type StockDetail as StockDetailData,
  type StockSummary,
} from "./api/client";
import { Home } from "./components/Home";
import { Discover } from "./components/Discover";
import { Holdings } from "./components/Holdings";
import { ResearchDigest } from "./components/ResearchDigest";
import { StockDetail } from "./components/StockDetail";
import { Skeleton } from "./components/ui/skeleton";
import { Alert } from "./components/ui/alert";

type View = "home" | "discover" | "holdings" | "research";
```

Add digest state right after the existing `holdings`/`holdingsError` state declarations:

```tsx
  const [holdings, setHoldings] = useState<Holding[] | null>(null);
  const [holdingsError, setHoldingsError] = useState<string | null>(null);
  const [newsDigest, setNewsDigest] = useState<NewsDigestEntry[] | null>(null);
  const [newsDigestError, setNewsDigestError] = useState<string | null>(null);
```

Add a fetch effect right after the existing holdings fetch effect:

```tsx
  useEffect(() => {
    if (view !== "research" || newsDigest !== null) return;
    fetchNewsDigest()
      .then(setNewsDigest)
      .catch((err) => setNewsDigestError(err.message));
  }, [view, newsDigest]);
```

Add a nav button, right after the existing "Holdings" button in the `<nav>` block:

```tsx
            <button
              type="button"
              className={navButtonClass(view === "research")}
              onClick={() => {
                setSelectedTicker(null);
                setView("research");
              }}
            >
              Research
            </button>
```

Add the render branch, right after the existing Holdings render branch:

```tsx
            {view === "holdings" && (
              <Holdings
                stocks={stocks ?? []}
                holdings={holdings}
                holdingsError={holdingsError}
                onHoldingAdded={(holding) =>
                  setHoldings((prev) => (prev ? [...prev, holding] : [holding]))
                }
                onSelectTicker={setSelectedTicker}
              />
            )}
            {view === "research" && (
              <ResearchDigest
                entries={newsDigest}
                error={newsDigestError}
                onSelectTicker={setSelectedTicker}
              />
            )}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx tsc --noEmit && npm test -- --run`
Expected: `tsc` produces no output; all test files pass (9 files, including the new App.tsx test).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: wire Research Digest screen into app navigation"
```

---

### Task 5: Final cross-module check

**Files:** none modified — verification only.

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest -v`
Expected: all tests pass, no regressions.

- [ ] **Step 2: Run the full frontend suite and build**

Run: `cd frontend && npm test -- --run && npm run build`
Expected: all tests pass; build succeeds; check `dist/assets/*.css` is non-trivial in size (known regression history in this repo — an empty Tailwind build passes `npm run build` silently).

- [ ] **Step 3: Manually verify in the browser**

With the backend (`uvicorn app.api.main:app --reload`) and frontend (`npm run dev`) both running, open the dev URL, click "Research", confirm it defaults to the most recent research date (2026-09-10, from today's automated run), shows the 13 researched stocks with correct confidence/red-flag badges, and that switching the date dropdown and tapping a row both work.
