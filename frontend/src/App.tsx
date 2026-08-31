import { useEffect, useState } from "react";
import { fetchStocks, type StockSummary } from "./api/client";
import { RankedTable } from "./components/RankedTable";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Skeleton } from "./components/ui/skeleton";
import { Alert } from "./components/ui/alert";

export function App() {
  const [stocks, setStocks] = useState<StockSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStocks()
      .then(setStocks)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-off-white text-ink-900 dark:bg-black dark:text-white">
      <header className="border-b border-lavender-100 bg-white/80 backdrop-blur dark:border-lavender-900/40 dark:bg-black/80">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-bold tracking-tight text-lavender-700 dark:text-lavender-300">
            Fintrixa
          </h1>
          <span className="text-xs text-ink-400">Indian equities screener</span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Ranked stocks</CardTitle>
          </CardHeader>
          <CardContent>
            {error && <Alert>{error}</Alert>}
            {!error && !stocks && (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            )}
            {stocks && <RankedTable stocks={stocks} />}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
