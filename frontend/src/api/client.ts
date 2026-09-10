export interface StockSummary {
  ticker: string;
  name: string;
  long_term_label: string | null;
  short_term_label: string | null;
  long_term_score: number | null;
  short_term_score: number | null;
  computed_at: string | null;
  explanation: string | null;
  excluded_reason: string | null;
}

export interface StockDetail extends StockSummary {
  fundamental_score: number | null;
  technical_score: number | null;
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

export interface HoldingGrading {
  verdict_in_effect: string | null;
  tracking_status:
    | "tracking_as_expected"
    | "not_tracking_as_expected"
    | "no_bullish_call"
    | "no_call_on_record";
  current_price: number | null;
  price_as_of_date: string | null;
  gain_loss_pct: number | null;
  gain_loss_abs: number | null;
}

export interface Holding {
  id: number;
  ticker: string;
  name: string;
  buy_price: number;
  quantity: number;
  buy_date: string;
  grading: HoldingGrading;
}

export interface HoldingCreateInput {
  ticker: string;
  buy_price: number;
  quantity: number;
  buy_date: string;
}

export async function fetchHoldings(): Promise<Holding[]> {
  const response = await fetch(`${API_BASE}/holdings`);
  if (!response.ok) {
    throw new Error(`failed to fetch holdings: ${response.status}`);
  }
  return response.json();
}

export async function createHolding(input: HoldingCreateInput): Promise<Holding> {
  const response = await fetch(`${API_BASE}/holdings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `failed to create holding: ${response.status}`);
  }
  return response.json();
}

export interface NewsDigestEntry {
  ticker: string;
  name: string;
  computed_at: string;
  confidence: string;
  red_flag_count: number;
}

export async function fetchNewsDigest(): Promise<NewsDigestEntry[]> {
  const response = await fetch(`${API_BASE}/news-digest`);
  if (!response.ok) {
    throw new Error(`failed to fetch news digest: ${response.status}`);
  }
  return response.json();
}
