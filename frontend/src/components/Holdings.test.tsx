import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { Holdings } from "./Holdings";
import * as client from "../api/client";
import type { Holding, StockSummary } from "../api/client";

const stocks: StockSummary[] = [
  {
    ticker: "RELIANCE.NS",
    name: "Reliance Industries",
    long_term_label: "Buy",
    short_term_label: "Hold",
    long_term_score: 78.4,
    short_term_score: 55.0,
    computed_at: "2026-08-31T18:00:00Z",
    explanation: null,
    excluded_reason: null,
  },
];

const trackingHolding: Holding = {
  id: 1,
  ticker: "RELIANCE.NS",
  name: "Reliance Industries",
  buy_price: 100,
  quantity: 10,
  buy_date: "2026-02-01",
  grading: {
    verdict_in_effect: "Buy",
    tracking_status: "tracking_as_expected",
    current_price: 120,
    price_as_of_date: "2026-03-01",
    gain_loss_pct: 20,
    gain_loss_abs: 200,
  },
};

test("shows an empty state when there are no holdings yet", () => {
  render(
    <Holdings stocks={stocks} holdings={[]} holdingsError={null} onHoldingAdded={vi.fn()} onSelectTicker={vi.fn()} />
  );
  expect(
    screen.getByText("No holdings logged yet — add your first buy above.")
  ).toBeInTheDocument();
});

test("renders a holding with its plain-English tracking sentence", () => {
  render(
    <Holdings
      stocks={stocks}
      holdings={[trackingHolding]}
      holdingsError={null}
      onHoldingAdded={vi.fn()}
      onSelectTicker={vi.fn()}
    />
  );
  expect(screen.getByRole("button", { name: /Reliance Industries/ })).toBeInTheDocument();
  expect(
    screen.getByText("AI called this Buy when you bought — it's up 20.0% since then.")
  ).toBeInTheDocument();
  expect(screen.getByText("Tracking as expected")).toBeInTheDocument();
});

test("renders the no-bullish-call sentence distinctly", () => {
  const holdHolding: Holding = {
    ...trackingHolding,
    id: 2,
    grading: {
      verdict_in_effect: "Hold",
      tracking_status: "no_bullish_call",
      current_price: 95,
      price_as_of_date: "2026-03-01",
      gain_loss_pct: -5,
      gain_loss_abs: -50,
    },
  };
  render(
    <Holdings stocks={stocks} holdings={[holdHolding]} holdingsError={null} onHoldingAdded={vi.fn()} onSelectTicker={vi.fn()} />
  );
  expect(
    screen.getByText("AI called this Hold when you bought — no bullish call to grade against.")
  ).toBeInTheDocument();
});

test("renders the not-tracking-as-expected sentence distinctly", () => {
  const laggingHolding: Holding = {
    ...trackingHolding,
    id: 3,
    grading: {
      verdict_in_effect: "Buy",
      tracking_status: "not_tracking_as_expected",
      current_price: 80,
      price_as_of_date: "2026-03-01",
      gain_loss_pct: -20,
      gain_loss_abs: -200,
    },
  };
  render(
    <Holdings stocks={stocks} holdings={[laggingHolding]} holdingsError={null} onHoldingAdded={vi.fn()} onSelectTicker={vi.fn()} />
  );
  expect(
    screen.getByText("AI called this Buy when you bought — it's down 20.0% since then.")
  ).toBeInTheDocument();
  expect(screen.getByText("Not tracking as expected")).toBeInTheDocument();
});

test("renders the no-call-on-record sentence distinctly", () => {
  const untrackedHolding: Holding = {
    ...trackingHolding,
    id: 4,
    grading: {
      verdict_in_effect: null,
      tracking_status: "no_call_on_record",
      current_price: 105,
      price_as_of_date: "2026-03-01",
      gain_loss_pct: 5,
      gain_loss_abs: 50,
    },
  };
  render(
    <Holdings stocks={stocks} holdings={[untrackedHolding]} holdingsError={null} onHoldingAdded={vi.fn()} onSelectTicker={vi.fn()} />
  );
  expect(screen.getByText("No AI call on record for this date.")).toBeInTheDocument();
  expect(screen.getByText("No AI call on record for this date")).toBeInTheDocument();
});

test("tapping a holding row calls onSelectTicker with its ticker", async () => {
  const user = userEvent.setup();
  const onSelectTicker = vi.fn();
  render(
    <Holdings
      stocks={stocks}
      holdings={[trackingHolding]}
      holdingsError={null}
      onHoldingAdded={vi.fn()}
      onSelectTicker={onSelectTicker}
    />
  );
  await user.click(screen.getByRole("button", { name: /Reliance Industries/ }));
  expect(onSelectTicker).toHaveBeenCalledWith("RELIANCE.NS");
});

test("submits the form and calls onHoldingAdded with the created holding", async () => {
  const user = userEvent.setup();
  const onHoldingAdded = vi.fn();
  vi.spyOn(client, "createHolding").mockResolvedValue(trackingHolding);

  render(
    <Holdings
      stocks={stocks}
      holdings={[]}
      holdingsError={null}
      onHoldingAdded={onHoldingAdded}
      onSelectTicker={vi.fn()}
    />
  );

  await user.type(screen.getByLabelText("Ticker"), "RELIANCE.NS");
  await user.type(screen.getByLabelText("Buy price"), "100");
  await user.type(screen.getByLabelText("Quantity"), "10");
  fireEvent.change(screen.getByLabelText("Buy date"), { target: { value: "2026-02-01" } });
  await user.click(screen.getByRole("button", { name: "Add holding" }));

  await waitFor(() => expect(onHoldingAdded).toHaveBeenCalledWith(trackingHolding));
  expect(client.createHolding).toHaveBeenCalledWith({
    ticker: "RELIANCE.NS",
    buy_price: 100,
    quantity: 10,
    buy_date: "2026-02-01",
  });
});

test("shows a form error when the API rejects the submission", async () => {
  const user = userEvent.setup();
  vi.spyOn(client, "createHolding").mockRejectedValue(
    new Error("we don't track this stock yet: NOPE.NS")
  );

  render(
    <Holdings stocks={stocks} holdings={[]} holdingsError={null} onHoldingAdded={vi.fn()} onSelectTicker={vi.fn()} />
  );

  await user.type(screen.getByLabelText("Ticker"), "NOPE.NS");
  await user.type(screen.getByLabelText("Buy price"), "100");
  await user.type(screen.getByLabelText("Quantity"), "10");
  fireEvent.change(screen.getByLabelText("Buy date"), { target: { value: "2026-02-01" } });
  await user.click(screen.getByRole("button", { name: "Add holding" }));

  expect(await screen.findByText("we don't track this stock yet: NOPE.NS")).toBeInTheDocument();
});
