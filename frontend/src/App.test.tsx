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
    explanation: null,
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

test("does not show stale detail data when the ticker changes before the first fetch resolves", async () => {
  const user = userEvent.setup();

  let resolveFirstDetail: (value: unknown) => void;
  let resolveSecondDetail: (value: unknown) => void;
  const firstDetailPromise = new Promise((resolve) => {
    resolveFirstDetail = resolve;
  });
  const secondDetailPromise = new Promise((resolve) => {
    resolveSecondDetail = resolve;
  });

  const detailSpy = vi.spyOn(client, "fetchStockDetail");
  detailSpy.mockReturnValueOnce(firstDetailPromise as never);
  detailSpy.mockReturnValueOnce(secondDetailPromise as never);
  vi.spyOn(client, "fetchStockHistory").mockResolvedValue([]);

  // Render with two stocks so we can select different tickers
  vi.spyOn(client, "fetchStocks").mockResolvedValueOnce([
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
    {
      ticker: "INFY.NS",
      name: "Infosys Limited",
      long_term_label: "Buy",
      short_term_label: "Buy",
      long_term_score: 82.5,
      short_term_score: 70.0,
      computed_at: "2026-08-31T18:00:00Z",
      excluded_reason: null,
    },
  ] as any);

  render(<App />);
  await screen.findByText("AI Picks Today");

  // Navigate to Discover to see the stock list
  await user.click(screen.getByRole("button", { name: "Discover" }));
  await screen.findByText("Every stock in our tracked universe, scored or not.");

  // Click on TCS.NS to start the first fetch
  await user.click(screen.getByText("Tata Consultancy Services"));

  // Before TCS.NS's fetch resolves, go back and select INFY.NS
  await user.click(screen.getByRole("button", { name: "Home" }));
  await user.click(screen.getByRole("button", { name: "Discover" }));
  await screen.findByText("Infosys Limited");
  await user.click(screen.getByText("Infosys Limited"));

  // Now resolve the fetches OUT OF ORDER:
  // 1. Resolve SECOND (INFY.NS) fetch FIRST (fresh data)
  // 2. Resolve FIRST (TCS.NS) fetch AFTER (stale data)

  const staleDetail = {
    ticker: "TCS.NS",
    name: "STALE - Tata Consultancy Services",
    long_term_label: "Hold",
    short_term_label: "Hold",
    long_term_score: 60.0,
    short_term_score: 45.0,
    fundamental_score: 50,
    technical_score: 50,
    computed_at: "2026-08-31T18:00:00Z",
    excluded_reason: null,
    explanation: "stale data",
  };

  const freshDetail = {
    ticker: "INFY.NS",
    name: "Infosys Limited",
    long_term_label: "Buy",
    short_term_label: "Buy",
    long_term_score: 82.5,
    short_term_score: 70.0,
    fundamental_score: 80,
    technical_score: 85,
    computed_at: "2026-08-31T18:00:00Z",
    excluded_reason: null,
    explanation: "strong fundamentals and technicals",
  };

  // Resolve SECOND fetch first (fresh data for INFY.NS)
  resolveSecondDetail!(freshDetail);
  // Then resolve FIRST fetch (stale data for TCS.NS)
  resolveFirstDetail!(staleDetail);

  // The page should show INFY.NS (fresh data), not TCS.NS stale data
  expect(await screen.findByText("Infosys Limited")).toBeInTheDocument();
  expect(screen.queryByText("STALE - Tata Consultancy Services")).not.toBeInTheDocument();
});
