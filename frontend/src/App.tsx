import { useEffect, useState } from "react";
import { fetchStocks, type StockSummary } from "./api/client";
import { RankedTable } from "./components/RankedTable";

export function App() {
  const [stocks, setStocks] = useState<StockSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStocks()
      .then(setStocks)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px" }}>
      <h1 style={{ color: "var(--lavender-700)" }}>Fintrixa</h1>
      {error && <p style={{ color: "var(--signal-avoid)" }}>{error}</p>}
      {!error && !stocks && <p>Loading…</p>}
      {stocks && <RankedTable stocks={stocks} />}
    </main>
  );
}
