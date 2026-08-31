import { VerdictBadge } from "./VerdictBadge";
import type { StockSummary } from "../api/client";

export type { StockSummary } from "../api/client";

export function RankedTable({ stocks }: { stocks: StockSummary[] }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ background: "var(--lavender-100)", textAlign: "left" }}>
          <th style={{ padding: "8px 12px" }}>Ticker</th>
          <th style={{ padding: "8px 12px" }}>Name</th>
          <th style={{ padding: "8px 12px" }}>Long-Term</th>
          <th style={{ padding: "8px 12px" }}>Short-Term</th>
        </tr>
      </thead>
      <tbody>
        {stocks.map((stock) => (
          <tr key={stock.ticker} style={{ borderBottom: "1px solid var(--border)" }}>
            <td style={{ padding: "8px 12px" }}>{stock.ticker}</td>
            <td style={{ padding: "8px 12px" }}>{stock.name}</td>
            <td style={{ padding: "8px 12px" }}>
              {stock.long_term_label ? (
                <VerdictBadge label={stock.long_term_label} />
              ) : (
                <span style={{ color: "var(--ink-400)" }}>{stock.excluded_reason}</span>
              )}
            </td>
            <td style={{ padding: "8px 12px" }}>
              {stock.short_term_label ? (
                <VerdictBadge label={stock.short_term_label} />
              ) : (
                <span style={{ color: "var(--ink-400)" }}>{stock.excluded_reason}</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
