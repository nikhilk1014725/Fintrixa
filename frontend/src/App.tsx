import { useEffect, useState } from "react";
import {
  fetchStockDetail,
  fetchStockHistory,
  fetchStocks,
  type PriceHistoryPoint,
  type StockDetail as StockDetailData,
  type StockSummary,
} from "./api/client";
import { Home } from "./components/Home";
import { Discover } from "./components/Discover";
import { StockDetail } from "./components/StockDetail";
import { Skeleton } from "./components/ui/skeleton";
import { Alert } from "./components/ui/alert";

type View = "home" | "discover";

export function App() {
  const [view, setView] = useState<View>("home");
  const [stocks, setStocks] = useState<StockSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [detail, setDetail] = useState<StockDetailData | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [history, setHistory] = useState<PriceHistoryPoint[] | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  useEffect(() => {
    fetchStocks()
      .then(setStocks)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedTicker) return;

    setDetail(null);
    setDetailError(null);
    setHistory(null);
    setHistoryError(null);

    fetchStockDetail(selectedTicker)
      .then(setDetail)
      .catch((err) => setDetailError(err.message));

    fetchStockHistory(selectedTicker)
      .then(setHistory)
      .catch((err) => setHistoryError(err.message));
  }, [selectedTicker]);

  function navButtonClass(active: boolean) {
    return active
      ? "rounded-md bg-lavender-100 px-3 py-1.5 text-sm font-semibold text-lavender-700 dark:bg-lavender-900/40 dark:text-lavender-300"
      : "rounded-md px-3 py-1.5 text-sm font-medium text-ink-400 hover:text-ink-900 dark:hover:text-white";
  }

  return (
    <div className="min-h-screen bg-off-white text-ink-900 dark:bg-black dark:text-white">
      <header className="border-b border-lavender-100 bg-white/80 backdrop-blur dark:border-lavender-900/40 dark:bg-black/80">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-bold tracking-tight text-lavender-700 dark:text-lavender-300">
            Fintrixa
          </h1>
          <nav className="flex gap-1">
            <button
              type="button"
              className={navButtonClass(view === "home")}
              onClick={() => {
                setSelectedTicker(null);
                setView("home");
              }}
            >
              Home
            </button>
            <button
              type="button"
              className={navButtonClass(view === "discover")}
              onClick={() => {
                setSelectedTicker(null);
                setView("discover");
              }}
            >
              Discover
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {selectedTicker ? (
          <StockDetail
            detail={detail}
            detailError={detailError}
            history={history}
            historyError={historyError}
            onBack={() => setSelectedTicker(null)}
          />
        ) : (
          <>
            {error && <Alert>{error}</Alert>}
            {!error && !stocks && (
              <div className="space-y-2">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            )}
            {stocks && view === "home" && (
              <Home stocks={stocks} onSelectTicker={setSelectedTicker} />
            )}
            {stocks && view === "discover" && (
              <Discover stocks={stocks} onSelectTicker={setSelectedTicker} />
            )}
          </>
        )}
      </main>
    </div>
  );
}
