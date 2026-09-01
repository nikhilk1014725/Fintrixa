import { StockCard } from "./StockCard";
import type { StockSummary } from "../api/client";

export function Discover({
  stocks,
  onSelectTicker,
}: {
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">Discover</h2>
      <p className="mt-1 text-sm text-ink-400">
        Every stock in our tracked universe, scored or not.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {stocks.map((stock) => (
          <StockCard key={stock.ticker} stock={stock} onSelect={onSelectTicker} />
        ))}
      </div>
    </div>
  );
}
