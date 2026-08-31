export interface StockSummary {
  ticker: string;
  name: string;
  long_term_label: string | null;
  short_term_label: string | null;
  long_term_score: number | null;
  short_term_score: number | null;
  computed_at: string | null;
  excluded_reason: string | null;
}

const API_BASE = "http://localhost:8000";

export async function fetchStocks(): Promise<StockSummary[]> {
  const response = await fetch(`${API_BASE}/stocks`);
  if (!response.ok) {
    throw new Error(`failed to fetch stocks: ${response.status}`);
  }
  return response.json();
}
