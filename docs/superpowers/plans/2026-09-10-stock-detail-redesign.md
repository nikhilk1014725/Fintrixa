# Stock Detail Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `StockDetail.tsx` into the plain-English sections described in `docs/superpowers/specs/2026-09-10-stock-detail-redesign-design.md` — last close price in the header, a renamed "In Simple Words" section, an always-visible "What could happen" (bull case) section, and a merged always-visible "What could go wrong" section (red flags + bear case) — using only fields the API already returns.

**Architecture:** Single-file frontend change. No backend, schema, or API changes — every field used (`explanation`, `news_bull_case`, `news_bear_case`, `news_red_flags`, `verdict_override_reason`, price history) already exists on `StockDetail`/`PriceHistoryPoint` in `frontend/src/api/client.ts`.

**Tech Stack:** React, TypeScript, Vitest + React Testing Library, Tailwind CSS v4.

---

## Task 1: Last close price in the header

**Files:**
- Modify: `frontend/src/components/StockDetail.tsx:126-150` (header block)
- Test: `frontend/src/components/StockDetail.test.tsx`

The header currently shows name, ticker, and verdict badges but no price. Add
the most recent price history point's close price, formatted with the
existing `formatDate` helper (already defined at `StockDetail.tsx:41-45`).
Only render it when `history` is a non-empty array — never show a
placeholder or a "live" price, since this is a historical close.

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/components/StockDetail.test.tsx` (after the existing
imports and `baseDetail`, alongside the other `test(...)` blocks):

```tsx
test("shows the most recent close price and date in the header when history has data", () => {
  render(
    <StockDetail
      detail={baseDetail}
      detailError={null}
      history={[
        { trade_date: "2026-08-29", open: 1800, high: 1810, low: 1790, close: 1805, volume: 100000 },
        { trade_date: "2026-08-30", open: 1805, high: 1850, low: 1800, close: 1842, volume: 120000 },
      ]}
      historyError={null}
      onBack={vi.fn()}
    />
  );

  expect(screen.getByText(/₹1,842\.00/)).toBeInTheDocument();
  expect(screen.getByText(/as of 30 Aug/)).toBeInTheDocument();
});

test("shows no price line in the header when history is empty", () => {
  render(
    <StockDetail
      detail={baseDetail}
      detailError={null}
      history={[]}
      historyError={null}
      onBack={vi.fn()}
    />
  );

  expect(screen.queryByText(/as of/)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run StockDetail`
Expected: FAIL — neither `₹1,842.00` nor `as of 30 Aug` is in the document
yet.

- [ ] **Step 3: Implement**

In `frontend/src/components/StockDetail.tsx`, change the header block (the
`<div className="mb-6 flex flex-wrap items-start justify-between gap-3">`
section) from:

```tsx
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">
            {detail.name}
          </h2>
          <p className="font-mono text-sm text-ink-400">{detail.ticker}</p>
        </div>
```

to:

```tsx
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">
            {detail.name}
          </h2>
          <p className="font-mono text-sm text-ink-400">{detail.ticker}</p>
          {history && history.length > 0 && (
            <p className="mt-1 text-sm text-ink-600 dark:text-lavender-200">
              ₹{history[history.length - 1].close.toFixed(2)} · as of{" "}
              {formatDate(history[history.length - 1].trade_date)}
            </p>
          )}
        </div>
```

(The rest of the header — the verdict badges `<div className="flex gap-2">...`
— is unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --run StockDetail`
Expected: PASS — both new tests pass, and no existing test breaks.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StockDetail.tsx frontend/src/components/StockDetail.test.tsx
git commit -m "feat: show last close price in stock detail header"
```

---

## Task 2: Restructure body into plain-English sections

**Files:**
- Modify: `frontend/src/components/StockDetail.tsx:152-240` (body sections, between header and "Show details" toggle)
- Test: `frontend/src/components/StockDetail.test.tsx`

This task does four things together, since they all touch the same JSX
block and reordering them separately would leave the component in a broken
intermediate state:

1. Rename "Suggested action" → "In Simple Words" (no behavior change).
2. Promote `news_bull_case` out of "Show details" into an always-visible
   "What could happen" section.
3. Merge the red-flags card and `news_bear_case` into one always-visible
   "What could go wrong" section — red-flag bullets keep the existing red
   styling; the bear case renders as plain (neutral) text in the same
   card; the section renders only when at least one of the two exists.
4. Remove bull/bear case from the "Show details" block, leaving only the
   confidence line and score breakdown there.

**Before writing code, read the current file** at
`frontend/src/components/StockDetail.tsx` (86–259) to confirm line numbers
match — if the file has drifted from what's shown in these steps, apply
the same logical changes rather than pasting blindly over different code.

- [ ] **Step 1: Write the failing tests**

Update `frontend/src/components/StockDetail.test.tsx`. Three existing
tests need to change because the behavior they assert on is moving; two
new tests need to be added.

**Replace** the existing test `"shows a red-flag warning card when active red flags are present"` with:

```tsx
test("shows red flags in the merged risk section when active red flags are present", () => {
  const withRedFlag: StockDetailData = {
    ...baseDetail,
    news_confidence: "Corroborated",
    news_bull_case: "bull",
    news_bear_case: "bear",
    news_red_flags: ["pending litigation over patent dispute"],
    news_researched_at: "2026-09-02T08:00:00Z",
    verdict_override_reason: "Active red flag(s) found: pending litigation over patent dispute",
  };

  render(
    <StockDetail detail={withRedFlag} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />
  );

  expect(screen.getByText("⚠ What could go wrong")).toBeInTheDocument();
  expect(screen.getAllByText(/pending litigation over patent dispute/).length).toBeGreaterThan(0);
});
```

**Replace** the existing test `"does not show a red-flag card when there are no red flags"` with:

```tsx
test("does not show the risk section when there are no red flags and no bear case", () => {
  render(<StockDetail detail={baseDetail} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />);

  expect(screen.queryByText("What could go wrong")).not.toBeInTheDocument();
  expect(screen.queryByText("⚠ What could go wrong")).not.toBeInTheDocument();
});
```

**Replace** the existing test `"shows bull/bear case and confidence in Show details when researched"` with:

```tsx
test("shows the bull case in What could happen and the bear case in What could go wrong without opening Show details", () => {
  const researched: StockDetailData = {
    ...baseDetail,
    news_confidence: "Corroborated",
    news_bull_case: "Strong order book.",
    news_bear_case: "Client concentration risk.",
    news_red_flags: [],
    news_researched_at: "2026-09-02T08:00:00Z",
    verdict_override_reason: null,
  };

  render(<StockDetail detail={researched} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />);

  expect(screen.getByText("What could happen")).toBeInTheDocument();
  expect(screen.getByText("Strong order book.")).toBeInTheDocument();
  expect(screen.getByText("What could go wrong")).toBeInTheDocument();
  expect(screen.getByText("Client concentration risk.")).toBeInTheDocument();
  expect(screen.queryByText(/Corroborated/)).not.toBeInTheDocument();
});

test("shows confidence only after opening Show details", async () => {
  const user = userEvent.setup();
  const researched: StockDetailData = {
    ...baseDetail,
    news_confidence: "Corroborated",
    news_bull_case: "Strong order book.",
    news_bear_case: "Client concentration risk.",
    news_red_flags: [],
    news_researched_at: "2026-09-02T08:00:00Z",
    verdict_override_reason: null,
  };

  render(<StockDetail detail={researched} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />);

  await user.click(screen.getByText("Show details"));

  expect(screen.getByText(/Corroborated/)).toBeInTheDocument();
});
```

**Add** a new test for the bear-case-only (no red flags) styling case:

```tsx
test("shows the bear case with a neutral (non-warning) title when there are no red flags", () => {
  const bearOnly: StockDetailData = {
    ...baseDetail,
    news_confidence: "Mixed",
    news_bull_case: null,
    news_bear_case: "Client concentration risk.",
    news_red_flags: [],
    news_researched_at: "2026-09-02T08:00:00Z",
    verdict_override_reason: null,
  };

  render(<StockDetail detail={bearOnly} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />);

  expect(screen.getByText("What could go wrong")).toBeInTheDocument();
  expect(screen.queryByText("⚠ What could go wrong")).not.toBeInTheDocument();
  expect(screen.getByText("Client concentration risk.")).toBeInTheDocument();
});
```

Also update the very first test in the file, `"renders the explanation text when a score is present"` — it doesn't need new assertions, but note that the card title text changed from "Suggested action" to "In Simple Words"; it doesn't currently assert on that title so no change needed there.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run StockDetail`
Expected: FAIL — the new/updated assertions (`"⚠ What could go wrong"`,
`"What could happen"`, `"What could go wrong"` without the click, confidence
absent before clicking Show details) don't match current output yet.

- [ ] **Step 3: Implement**

In `frontend/src/components/StockDetail.tsx`, replace the whole block from
the `<Card className="mb-6 border-lavender-300/60...">` ("Suggested
action") through the closing of the old red-flags `<Card>` (i.e. from just
after the header `</div>` down to just before the `<button ... Show
details`) with:

```tsx
      <Card className="mb-6 border-lavender-300/60 bg-lavender-50 dark:border-lavender-500/30 dark:bg-lavender-900/20">
        <CardHeader>
          <CardTitle className="text-base">In Simple Words</CardTitle>
        </CardHeader>
        <CardContent>
          {hasScore && detail.explanation ? (
            <p className="text-base leading-snug text-ink-900 dark:text-white">
              {detail.explanation}
            </p>
          ) : (
            <p className="text-sm leading-snug text-ink-600 dark:text-lavender-100">
              {detail.excluded_reason ?? "No verdict available for this stock yet."}
            </p>
          )}
        </CardContent>
      </Card>

      {detail.news_bull_case && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">What could happen</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-ink-900 dark:text-white">{detail.news_bull_case}</p>
          </CardContent>
        </Card>
      )}

      {(() => {
        const hasRedFlags = Boolean(detail.news_red_flags && detail.news_red_flags.length > 0);
        const hasBearCase = Boolean(detail.news_bear_case);
        if (!hasRedFlags && !hasBearCase) return null;

        return (
          <Card
            className={
              hasRedFlags
                ? "mb-6 border-signal-avoid/40 bg-signal-avoid/15"
                : "mb-6"
            }
          >
            <CardHeader>
              <CardTitle className={hasRedFlags ? "text-base text-signal-avoid" : "text-base"}>
                {hasRedFlags ? "⚠ What could go wrong" : "What could go wrong"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {hasRedFlags && (
                <ul className="list-disc space-y-1 pl-5 text-sm text-ink-900 dark:text-white">
                  {detail.news_red_flags!.map((flag, i) => (
                    <li key={i}>{flag}</li>
                  ))}
                </ul>
              )}
              {hasBearCase && (
                <p className={hasRedFlags ? "mt-3 text-sm text-ink-900 dark:text-white" : "text-sm text-ink-900 dark:text-white"}>
                  {detail.news_bear_case}
                </p>
              )}
              {detail.verdict_override_reason && (
                <p className="mt-3 text-xs text-ink-400">{detail.verdict_override_reason}</p>
              )}
            </CardContent>
          </Card>
        );
      })()}
```

Then, in the `showDetails && detail.news_researched_at` block (the "News
research" card), remove the bull case and bear case blocks, leaving only
the confidence line:

```tsx
      {showDetails && detail.news_researched_at && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">News research</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs uppercase tracking-wide text-ink-400">
              Confidence: {detail.news_confidence}
            </p>
          </CardContent>
        </Card>
      )}
```

The "Show details" toggle button and the score-breakdown `Card` above it
are unchanged. The price-history `Card` at the bottom is unchanged and
stays last.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --run StockDetail`
Expected: PASS — all tests in the file pass, including the two from
Task 1.

- [ ] **Step 5: Run the full frontend test suite and type check**

Run: `cd frontend && npx tsc --noEmit && npm test -- --run`
Expected: PASS — no regressions in any other component (`Home.test.tsx`,
`Discover.test.tsx`, `Holdings.test.tsx`, `ResearchDigest.test.tsx`,
`App.test.tsx`, etc.), since no other file imports internals of
`StockDetail.tsx` beyond the exported `StockDetail` component itself.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/StockDetail.tsx frontend/src/components/StockDetail.test.tsx
git commit -m "feat: reorganize stock detail into plain-English sections"
```

---

## Self-Review Notes

- **Spec coverage:** Header price (Task 1, spec §1); "In Simple Words"
  rename (Task 2 step 3, spec §2); "What could happen" bull case (Task 2,
  spec §4); merged "What could go wrong" (Task 2, spec §3); Show details
  narrowed to score breakdown + confidence (Task 2, spec §5); section
  order — header → In Simple Words → What could happen → What could go
  wrong → Show details → price chart (spec §6) — matches the JSX order
  produced by Task 2's replacement block followed by the untouched score
  breakdown/chart code. All six spec items are covered by two tasks.
- **Placeholder scan:** none found — every step has literal code and exact
  commands.
- **Type consistency:** no new types introduced; all fields referenced
  (`news_bull_case`, `news_bear_case`, `news_red_flags`,
  `verdict_override_reason`, `news_confidence`, `news_researched_at`,
  `explanation`, `excluded_reason`, `PriceHistoryPoint.close`,
  `PriceHistoryPoint.trade_date`) already exist on the types in
  `frontend/src/api/client.ts` and are used with their existing names
  throughout.
