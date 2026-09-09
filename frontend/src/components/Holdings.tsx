import { useState, type FormEvent, type KeyboardEvent } from "react";
import { createHolding } from "../api/client";
import type { Holding, StockSummary } from "../api/client";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Alert } from "./ui/alert";

const TRACKING_STATUS_COPY: Record<Holding["grading"]["tracking_status"], string> = {
  tracking_as_expected: "Tracking as expected",
  not_tracking_as_expected: "Not tracking as expected",
  no_bullish_call: "No bullish call to grade against",
  no_call_on_record: "No AI call on record for this date",
};

const TRACKING_STATUS_VARIANT: Record<
  Holding["grading"]["tracking_status"],
  "strong-buy" | "hold" | "neutral"
> = {
  tracking_as_expected: "strong-buy",
  not_tracking_as_expected: "hold",
  no_bullish_call: "neutral",
  no_call_on_record: "neutral",
};

function trackingSentence(holding: Holding): string {
  const { grading } = holding;
  if (grading.tracking_status === "no_call_on_record") {
    return "No AI call on record for this date.";
  }
  if (grading.tracking_status === "no_bullish_call") {
    return `AI called this ${grading.verdict_in_effect ?? "Hold"} when you bought — no bullish call to grade against.`;
  }
  const direction = grading.tracking_status === "tracking_as_expected" ? "up" : "down";
  const pct = grading.gain_loss_pct !== null ? Math.abs(grading.gain_loss_pct).toFixed(1) : "0.0";
  return `AI called this ${grading.verdict_in_effect} when you bought — it's ${direction} ${pct}% since then.`;
}

export function Holdings({
  stocks,
  holdings,
  holdingsError,
  onHoldingAdded,
  onSelectTicker,
}: {
  stocks: StockSummary[];
  holdings: Holding[] | null;
  holdingsError: string | null;
  onHoldingAdded: (holding: Holding) => void;
  onSelectTicker: (ticker: string) => void;
}) {
  const [ticker, setTicker] = useState("");
  const [buyPrice, setBuyPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [buyDate, setBuyDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const holding = await createHolding({
        ticker,
        buy_price: Number(buyPrice),
        quantity: Number(quantity),
        buy_date: buyDate,
      });
      onHoldingAdded(holding);
      setTicker("");
      setBuyPrice("");
      setQuantity("");
      setBuyDate("");
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">My Holdings</h2>
      <p className="mt-1 text-sm text-ink-400">
        Log what you bought and see whether the AI's call has held up.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-ink-400" htmlFor="holding-ticker">
            Ticker
          </label>
          <input
            id="holding-ticker"
            list="known-tickers"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            required
            className="mt-1 rounded-md border border-lavender-100 px-2 py-1.5 text-sm dark:border-lavender-900/40 dark:bg-black"
          />
          <datalist id="known-tickers">
            {stocks.map((stock) => (
              <option key={stock.ticker} value={stock.ticker}>
                {stock.name}
              </option>
            ))}
          </datalist>
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-400" htmlFor="holding-buy-price">
            Buy price
          </label>
          <input
            id="holding-buy-price"
            type="number"
            step="0.01"
            value={buyPrice}
            onChange={(e) => setBuyPrice(e.target.value)}
            required
            className="mt-1 w-28 rounded-md border border-lavender-100 px-2 py-1.5 text-sm dark:border-lavender-900/40 dark:bg-black"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-400" htmlFor="holding-quantity">
            Quantity
          </label>
          <input
            id="holding-quantity"
            type="number"
            step="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
            className="mt-1 w-24 rounded-md border border-lavender-100 px-2 py-1.5 text-sm dark:border-lavender-900/40 dark:bg-black"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-400" htmlFor="holding-buy-date">
            Buy date
          </label>
          <input
            id="holding-buy-date"
            type="date"
            value={buyDate}
            onChange={(e) => setBuyDate(e.target.value)}
            required
            className="mt-1 rounded-md border border-lavender-100 px-2 py-1.5 text-sm dark:border-lavender-900/40 dark:bg-black"
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-lavender-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-lavender-700 disabled:opacity-50"
        >
          Add holding
        </button>
      </form>

      {formError && <Alert className="mt-4">{formError}</Alert>}
      {holdingsError && <Alert className="mt-4">{holdingsError}</Alert>}

      {!holdingsError && holdings && holdings.length === 0 && (
        <p className="mt-8 text-sm text-ink-400">No holdings logged yet — add your first buy above.</p>
      )}

      {holdings && holdings.length > 0 && (
        <div className="mt-6 space-y-3">
          {holdings.map((holding) => {
            function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectTicker(holding.ticker);
              }
            }

            return (
              <Card
                key={holding.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectTicker(holding.ticker)}
                onKeyDown={handleKeyDown}
                className="cursor-pointer p-4 transition hover:border-lavender-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:hover:border-lavender-500/40"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-base font-semibold text-ink-900 dark:text-white">{holding.name}</div>
                    <div className="font-mono text-xs text-ink-400">{holding.ticker}</div>
                  </div>
                  <Badge variant={TRACKING_STATUS_VARIANT[holding.grading.tracking_status]}>
                    {TRACKING_STATUS_COPY[holding.grading.tracking_status]}
                  </Badge>
                </div>
                <p className="mt-3 text-sm text-ink-600 dark:text-lavender-300">{trackingSentence(holding)}</p>
                <div className="mt-2 text-xs text-ink-400">
                  Bought {holding.quantity} @ ₹{holding.buy_price} on {holding.buy_date}
                  {holding.grading.current_price !== null && (
                    <>
                      {" "}
                      — current price ₹{holding.grading.current_price}
                      {holding.grading.price_as_of_date &&
                        holding.grading.price_as_of_date !== holding.buy_date && (
                          <> as of {holding.grading.price_as_of_date}</>
                        )}
                    </>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
