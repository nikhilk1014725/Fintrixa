import { useMemo, useState, type KeyboardEvent } from "react";
import type { NewsDigestEntry } from "../api/client";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Alert } from "./ui/alert";

function formatDateLabel(dateKey: string): string {
  const d = new Date(`${dateKey}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateKey;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function groupByDate(entries: NewsDigestEntry[]): Map<string, NewsDigestEntry[]> {
  const groups = new Map<string, NewsDigestEntry[]>();
  const seen = new Set<string>();
  for (const entry of entries) {
    const dateKey = entry.computed_at.slice(0, 10);
    const dedupeKey = `${dateKey}|${entry.ticker}`;
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);
    const group = groups.get(dateKey);
    if (group) {
      group.push(entry);
    } else {
      groups.set(dateKey, [entry]);
    }
  }
  return groups;
}

export function ResearchDigest({
  entries,
  error,
  onSelectTicker,
}: {
  entries: NewsDigestEntry[] | null;
  error: string | null;
  onSelectTicker: (ticker: string) => void;
}) {
  const groups = useMemo(() => (entries ? groupByDate(entries) : new Map<string, NewsDigestEntry[]>()), [
    entries,
  ]);
  const dates = useMemo(() => Array.from(groups.keys()).sort().reverse(), [groups]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const activeDate = selectedDate && dates.includes(selectedDate) ? selectedDate : (dates[0] ?? null);
  const rows = activeDate ? (groups.get(activeDate) ?? []) : [];

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-ink-900 dark:text-white">Research Digest</h2>
      <p className="mt-1 text-sm text-ink-400">
        What the daily AI news research found, one day at a time.
      </p>

      {error && <Alert className="mt-4">{error}</Alert>}

      {!error && entries && entries.length === 0 && (
        <p className="mt-8 text-sm text-ink-400">No research has been logged yet.</p>
      )}

      {!error && dates.length > 0 && activeDate && (
        <>
          <label className="mt-6 block text-xs font-medium text-ink-400" htmlFor="digest-date">
            Date
          </label>
          <select
            id="digest-date"
            value={activeDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="mt-1 rounded-md border border-lavender-100 px-2 py-1.5 text-sm dark:border-lavender-900/40 dark:bg-black"
          >
            {dates.map((date) => (
              <option key={date} value={date}>
                {formatDateLabel(date)}
              </option>
            ))}
          </select>

          <div className="mt-4 space-y-3">
            {rows.map((entry) => {
              function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectTicker(entry.ticker);
                }
              }

              return (
                <Card
                  key={entry.ticker}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectTicker(entry.ticker)}
                  onKeyDown={handleKeyDown}
                  className="cursor-pointer p-4 transition hover:border-lavender-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-lavender-500 dark:hover:border-lavender-500/40"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-base font-semibold text-ink-900 dark:text-white">
                        {entry.name}
                      </div>
                      <div className="font-mono text-xs text-ink-400">{entry.ticker}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="neutral">{entry.confidence}</Badge>
                      {entry.red_flag_count > 0 && (
                        <Badge variant="avoid">
                          {entry.red_flag_count} red flag{entry.red_flag_count > 1 ? "s" : ""}
                        </Badge>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
