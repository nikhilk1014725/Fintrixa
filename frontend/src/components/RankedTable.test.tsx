import { render, screen } from "@testing-library/react";
import { RankedTable, type StockSummary } from "./RankedTable";

const stocks: StockSummary[] = [
  {
    ticker: "RELIANCE.NS",
    name: "Reliance Industries",
    long_term_label: "Buy",
    short_term_label: "Hold",
    long_term_score: 78.4,
    short_term_score: 55.0,
    computed_at: "2026-08-31T18:00:00Z",
    excluded_reason: null,
  },
];

test("renders a row per stock with its long-term verdict label", () => {
  render(<RankedTable stocks={stocks} />);
  expect(screen.getByText("RELIANCE.NS")).toBeInTheDocument();
  expect(screen.getByText("Buy")).toBeInTheDocument();
});

test("renders excluded reason instead of a score when present", () => {
  const excluded: StockSummary[] = [
    { ...stocks[0], long_term_label: null, excluded_reason: "not yet scored" },
  ];
  render(<RankedTable stocks={excluded} />);
  expect(screen.getByText("not yet scored")).toBeInTheDocument();
});
