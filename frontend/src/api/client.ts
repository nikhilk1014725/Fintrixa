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

export interface StockDetail extends StockSummary {
  fundamental_score: number | null;
  technical_score: number | null;
  explanation: string | null;
  news_confidence: string | null;
  news_bull_case: string | null;
  news_bear_case: string | null;
  news_red_flags: string[] | null;
  news_researched_at: string | null;
  verdict_override_reason: string | null;
}

export interface PriceHistoryPoint {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const API_BASE = "http://localhost:8000";

export async function fetchStocks(): Promise<StockSummary[]> {
  const response = await fetch(`${API_BASE}/stocks`);
  if (!response.ok) {
    throw new Error(`failed to fetch stocks: ${response.status}`);
  }
  return response.json();
}

export async function fetchStockDetail(ticker: string): Promise<StockDetail> {
  const response = await fetch(`${API_BASE}/stocks/${ticker}`);
  if (!response.ok) {
    throw new Error(`failed to fetch stock detail: ${response.status}`);
  }
  return response.json();
}

export async function fetchStockHistory(ticker: string): Promise<PriceHistoryPoint[]> {
  const response = await fetch(`${API_BASE}/stocks/${ticker}/history`);
  if (!response.ok) {
    throw new Error(`failed to fetch stock history: ${response.status}`);
  }
  return response.json();
}
