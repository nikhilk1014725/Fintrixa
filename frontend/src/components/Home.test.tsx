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
