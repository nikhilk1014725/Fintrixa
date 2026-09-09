import { StockCard } from "./StockCard";
import type { StockSummary } from "../api/client";

const BEST_TODAY_LABELS = new Set(["Strong Buy", "Buy"]);

function isLongTermPick(
  stock: StockSummary
): stock is StockSummary & { long_term_score: number } {
  return stock.long_term_label !== null && stock.long_term_score !== null;
}

function isShortTermPick(
  stock: StockSummary
): stock is StockSummary & { short_term_score: number } {
  return stock.short_term_label !== null && stock.short_term_score !== null;
}

function qualifiesForBestToday(stock: StockSummary): boolean {
  const longQualifies =
    stock.long_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.long_term_label) &&
    stock.long_term_score !== null;
  const shortQualifies =
    stock.short_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.short_term_label) &&
    stock.short_term_score !== null;
  return longQualifies || shortQualifies;
}

function bestTodayRank(stock: StockSummary): number {
  const longRank =
    stock.long_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.long_term_label) &&
    stock.long_term_score !== null
      ? stock.long_term_score
      : Number.NEGATIVE_INFINITY;
  const shortRank =
    stock.short_term_label !== null &&
    BEST_TODAY_LABELS.has(stock.short_term_label) &&
    stock.short_term_score !== null
      ? stock.short_term_score
      : Number.NEGATIVE_INFINITY;
  return Math.max(longRank, shortRank);
}

function CategorySection({
  title,
  emptyMessage,
  stocks,
  onSelectTicker,
}: {
  title: string;
  emptyMessage: string;
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  return (
    <section aria-label={title} className="mt-8 first:mt-6">
      <h3 className="text-lg font-semibold text-ink-900 dark:text-white">{title}</h3>
      {stocks.length === 0 ? (
        <p className="mt-4 text-sm text-ink-400">{emptyMessage}</p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {stocks.map((stock) => (
            <StockCard key={stock.ticker} stock={stock} onSelect={onSelectTicker} />
          ))}
        </div>
      )}
    </section>
  );
}

export function Home({
  stocks,
  onSelectTicker,
}: {
  stocks: StockSummary[];
  onSelectTicker: (ticker: string) => void;
}) {
  const bestToday = stocks
    .filter(qualifiesForBestToday)
    .sort((a, b) => bestTodayRank(b) - bestTodayRank(a));

  const longTermPicks = stocks
    .filter(isLongTermPick)
    .sort((a, b) => b.long_term_score - a.long_term_score);

  const shortTermPicks = stocks
    .filter(isShortTermPick)
    .sort((a, b) => b.short_term_score - a.short_term_score);

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">
        AI Picks Today
      </h2>
      <p className="mt-1 text-sm text-ink-400">
        Screened from our tracked universe of {stocks.length} Indian stocks.
      </p>

      <CategorySection
        title="Best Today"
        emptyMessage="No strong opportunity today — check back after the next scoring run."
        stocks={bestToday}
        onSelectTicker={onSelectTicker}
      />
      <CategorySection
        title="Long-Term Picks"
        emptyMessage="No long-term opportunities right now. Check back after the next scoring run."
        stocks={longTermPicks}
        onSelectTicker={onSelectTicker}
      />
      <CategorySection
        title="Short-Term Picks"
        emptyMessage="No short-term opportunities right now. Check back after the next scoring run."
        stocks={shortTermPicks}
        onSelectTicker={onSelectTicker}
      />
    </div>
  );
}
