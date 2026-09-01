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
