import { StockCard } from "./StockCard";
import type { StockSummary } from "../api/client";

export function Home({
  stocks,
  onSelectTicker,
}: {
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  const ranked = stocks
    .filter((stock) => stock.long_term_label !== null || stock.short_term_label !== null)
    .sort(
      (a, b) =>
        (b.long_term_score ?? b.short_term_score ?? 0) -
        (a.long_term_score ?? a.short_term_score ?? 0)
    );

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">
        AI Picks Today
      </h2>
      <p className="mt-1 text-sm text-ink-400">
        Screened from our tracked universe of {stocks.length} Indian stocks.
      </p>

      {ranked.length === 0 ? (
        <p className="mt-8 text-sm text-ink-400">
          No strong opportunities right now. Check back after the next scoring run.
        </p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {ranked.map((stock) => (
            <StockCard key={stock.ticker} stock={stock} onSelect={onSelectTicker} />
          ))}
        </div>
      )}
    </div>
  );
}
