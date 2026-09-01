import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StockDetail as StockDetailData, PriceHistoryPoint } from "../api/client";
import { VerdictBadge } from "./VerdictBadge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Skeleton } from "./ui/skeleton";
import { Alert } from "./ui/alert";

function BackButton({ onBack }: { onBack: () => void }) {
  return (
    <button
      type="button"
      onClick={onBack}
      className="mb-4 inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-lavender-700 hover:bg-lavender-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:text-lavender-300 dark:hover:bg-lavender-900/20"
    >
      &larr; Back to ranked stocks
    </button>
  );
}

function ScoreTile({ label, score }: { label: string; score: number | null }) {
  return (
    <div className="rounded-lg border border-lavender-100 bg-off-white px-4 py-3 dark:border-lavender-900/40 dark:bg-black/40">
      <div className="text-xs font-semibold uppercase tracking-wide text-ink-400">{label}</div>
      <div className="mt-1 text-2xl font-bold text-ink-900 dark:text-white">
        {score !== null ? Math.round(score) : "—"}
        <span className="text-sm font-normal text-ink-400"> /100</span>
      </div>
    </div>
  );
}

function formatDate(value: string) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function PriceChart({ history }: { history: PriceHistoryPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={history} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8e6fd1" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#8e6fd1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e8e1f5" />
        <XAxis
          dataKey="trade_date"
          tickFormatter={formatDate}
          tick={{ fontSize: 12, fill: "#85809a" }}
          minTickGap={24}
        />
        <YAxis
          domain={["auto", "auto"]}
          tick={{ fontSize: 12, fill: "#85809a" }}
          width={56}
        />
        <Tooltip
          labelFormatter={(value) => formatDate(String(value))}
          formatter={(value) => [`₹${Number(value).toFixed(2)}`, "Close"]}
          contentStyle={{ borderRadius: 8, borderColor: "#e8e1f5", fontSize: 12 }}
        />
        <Area
          type="monotone"
          dataKey="close"
          stroke="#8e6fd1"
          strokeWidth={2}
          fill="url(#priceFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function StockDetail({
  detail,
  detailError,
  history,
  historyError,
  onBack,
}: {
  detail: StockDetailData | null;
  detailError: string | null;
  history: PriceHistoryPoint[] | null;
  historyError: string | null;
  onBack: () => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  if (detailError) {
    return (
      <div>
        <BackButton onBack={onBack} />
        <Alert>{detailError}</Alert>
      </div>
    );
  }

  if (!detail) {
    return (
      <div>
        <BackButton onBack={onBack} />
        <div className="space-y-3">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    );
  }

  const hasScore = detail.long_term_label !== null || detail.short_term_label !== null;

  return (
    <div>
      <BackButton onBack={onBack} />

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">
            {detail.name}
          </h2>
          <p className="font-mono text-sm text-ink-400">{detail.ticker}</p>
        </div>
        <div className="flex gap-2">
          {detail.long_term_label && (
            <div className="text-right">
              <div className="text-[11px] uppercase tracking-wide text-ink-400">Long-term</div>
              <VerdictBadge label={detail.long_term_label} />
            </div>
          )}
          {detail.short_term_label && (
            <div className="text-right">
              <div className="text-[11px] uppercase tracking-wide text-ink-400">Short-term</div>
              <VerdictBadge label={detail.short_term_label} />
            </div>
          )}
        </div>
      </div>

      <Card className="mb-6 border-lavender-300/60 bg-lavender-50 dark:border-lavender-500/30 dark:bg-lavender-900/20">
        <CardHeader>
          <CardTitle className="text-base">Suggested action</CardTitle>
        </CardHeader>
        <CardContent>
          {hasScore && detail.explanation ? (
            <p className="text-base leading-snug text-ink-900 dark:text-white">
              {detail.explanation}
            </p>
          ) : (
            <p className="text-sm leading-snug text-ink-600 dark:text-lavender-100">
              {detail.excluded_reason ?? "No verdict available for this stock yet."}
            </p>
          )}
        </CardContent>
      </Card>

      <button
        type="button"
        onClick={() => setShowDetails((value) => !value)}
        className="mb-6 inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-lavender-700 hover:bg-lavender-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:text-lavender-300 dark:hover:bg-lavender-900/20"
      >
        {showDetails ? "Hide details" : "Show details"}
      </button>

      {showDetails && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Score breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <ScoreTile label="Fundamental" score={detail.fundamental_score} />
              <ScoreTile label="Technical" score={detail.technical_score} />
            </div>
            <p className="mt-3 text-xs text-ink-400">
              Long-term verdict weights fundamentals 70% / technicals 30%. Short-term verdict
              weights technicals 70% / fundamentals 30%.
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Price history</CardTitle>
        </CardHeader>
        <CardContent>
          {historyError && <Alert>{historyError}</Alert>}
          {!historyError && history === null && <Skeleton className="h-[240px] w-full" />}
          {!historyError && history !== null && history.length === 0 && (
            <p className="text-sm text-ink-400">No price history yet.</p>
          )}
          {!historyError && history !== null && history.length > 0 && (
            <PriceChart history={history} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
