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
  explanation: "Strong business, healthy balance sheet, attractive long-term growth potential.",
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

test("renders the explanation sentence when present", () => {
  render(<StockCard stock={stock} onSelect={vi.fn()} />);
  expect(
    screen.getByText(
      "Strong business, healthy balance sheet, attractive long-term growth potential."
    )
  ).toBeInTheDocument();
});

test("renders nothing extra when explanation is null", () => {
  const noExplanation: StockSummary = { ...stock, explanation: null };
  render(<StockCard stock={noExplanation} onSelect={vi.fn()} />);
  expect(
    screen.queryByText(
      "Strong business, healthy balance sheet, attractive long-term growth potential."
    )
  ).not.toBeInTheDocument();
});
