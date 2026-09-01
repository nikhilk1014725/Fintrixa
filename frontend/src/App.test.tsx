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
