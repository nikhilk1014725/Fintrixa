import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { StockDetail } from "./StockDetail";
import type { StockDetail as StockDetailData } from "../api/client";

const baseDetail: StockDetailData = {
  ticker: "RELIANCE.NS",
  name: "Reliance Industries",
  long_term_label: "Buy",
  short_term_label: "Hold",
  long_term_score: 72,
  short_term_score: 55,
  fundamental_score: 72,
  technical_score: 65,
  computed_at: "2026-08-31T18:00:00Z",
  excluded_reason: null,
  explanation:
    "Long-term: buy on fundamentals (72/100) with technicals at 65/100. Short-term: hold on current momentum.",
  news_confidence: null,
  news_bull_case: null,
  news_bear_case: null,
  news_red_flags: null,
  news_researched_at: null,
  verdict_override_reason: null,
};

test("renders the explanation text when a score is present", () => {
  render(
    <StockDetail
      detail={baseDetail}
      detailError={null}
      history={[]}
      historyError={null}
      onBack={vi.fn()}
    />
  );

  expect(screen.getByText(/buy on fundamentals \(72\/100\)/)).toBeInTheDocument();
  expect(screen.getByText("RELIANCE.NS")).toBeInTheDocument();
});

test("renders the excluded reason instead of a blank card when there is no score", () => {
  const excluded: StockDetailData = {
    ...baseDetail,
    long_term_label: null,
    short_term_label: null,
    long_term_score: null,
    short_term_score: null,
    fundamental_score: null,
    technical_score: null,
    explanation: null,
    excluded_reason: "not yet scored",
  };

  render(
    <StockDetail
      detail={excluded}
      detailError={null}
      history={[]}
      historyError={null}
      onBack={vi.fn()}
    />
  );

  expect(screen.getByText("not yet scored")).toBeInTheDocument();
});

test("shows an empty state instead of a broken chart when history is empty", () => {
  render(
    <StockDetail
      detail={baseDetail}
      detailError={null}
      history={[]}
      historyError={null}
      onBack={vi.fn()}
    />
  );

  expect(screen.getByText("No price history yet.")).toBeInTheDocument();
});

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

test("does not show the risk section when there are no red flags and no bear case", () => {
  render(<StockDetail detail={baseDetail} detailError={null} history={[]} historyError={null} onBack={vi.fn()} />);

  expect(screen.queryByText("What could go wrong")).not.toBeInTheDocument();
  expect(screen.queryByText("⚠ What could go wrong")).not.toBeInTheDocument();
});

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
