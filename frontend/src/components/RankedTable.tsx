import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { VerdictBadge } from "./VerdictBadge";
import type { StockSummary } from "../api/client";

export type { StockSummary } from "../api/client";

export function RankedTable({ stocks }: { stocks: StockSummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Name</TableHead>
          <TableHead>Long-Term</TableHead>
          <TableHead>Short-Term</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {stocks.map((stock) => (
          <TableRow key={stock.ticker}>
            <TableCell className="font-mono font-medium">{stock.ticker}</TableCell>
            <TableCell className="text-ink-600 dark:text-lavender-100">{stock.name}</TableCell>
            <TableCell>
              {stock.long_term_label ? (
                <VerdictBadge label={stock.long_term_label} />
              ) : (
                <span className="text-xs text-ink-400">{stock.excluded_reason}</span>
              )}
            </TableCell>
            <TableCell>
              {stock.short_term_label ? (
                <VerdictBadge label={stock.short_term_label} />
              ) : (
                <span className="text-xs text-ink-400">{stock.excluded_reason}</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
