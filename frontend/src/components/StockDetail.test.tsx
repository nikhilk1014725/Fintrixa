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
