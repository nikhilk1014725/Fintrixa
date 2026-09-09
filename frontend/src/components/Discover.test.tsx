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
    explanation: null,
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
