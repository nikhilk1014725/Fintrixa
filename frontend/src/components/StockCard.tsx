import type { KeyboardEvent } from "react";
import { VerdictBadge } from "./VerdictBadge";
import { Card } from "./ui/card";
import type { StockSummary } from "../api/client";

export function StockCard({
  stock,
  onSelect,
}: {
  stock: StockSummary;
  onSelect: (ticker: string) => void;
}) {
  const hasVerdict = stock.long_term_label !== null || stock.short_term_label !== null;

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(stock.ticker);
    }
  }

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => onSelect(stock.ticker)}
      onKeyDown={handleKeyDown}
      className="cursor-pointer p-5 transition hover:border-lavender-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:hover:border-lavender-500/40"
    >
      <div className="text-base font-semibold text-ink-900 dark:text-white">{stock.name}</div>
      <div className="font-mono text-xs text-ink-400">{stock.ticker}</div>

      {hasVerdict ? (
        <div className="mt-4 flex flex-wrap gap-4">
          {stock.long_term_label && (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-ink-400">Long-term</div>
              <VerdictBadge label={stock.long_term_label} />
              {stock.long_term_score !== null && (
                <div className="mt-1 text-xs text-ink-400">
                  {Math.round(stock.long_term_score)}/100
                </div>
              )}
            </div>
          )}
          {stock.short_term_label && (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-ink-400">Short-term</div>
              <VerdictBadge label={stock.short_term_label} />
              {stock.short_term_score !== null && (
                <div className="mt-1 text-xs text-ink-400">
                  {Math.round(stock.short_term_score)}/100
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <p className="mt-4 text-xs text-ink-400">{stock.excluded_reason}</p>
      )}

      {stock.explanation && (
        <p className="mt-3 text-xs text-ink-500 dark:text-ink-300">{stock.explanation}</p>
      )}
    </Card>
  );
}
