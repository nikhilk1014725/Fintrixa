import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ResearchDigest } from "./ResearchDigest";
import type { NewsDigestEntry } from "../api/client";

const entries: NewsDigestEntry[] = [
  {
    ticker: "RELIANCE.NS",
    name: "Reliance Industries",
    computed_at: "2026-09-10T08:05:00Z",
    confidence: "Mixed",
    red_flag_count: 2,
  },
  {
    ticker: "TCS.NS",
    name: "Tata Consultancy Services",
    computed_at: "2026-09-10T08:00:00Z",
    confidence: "Corroborated",
    red_flag_count: 0,
  },
  {
    ticker: "TCS.NS",
    name: "Tata Consultancy Services",
    computed_at: "2026-09-09T08:00:00Z",
    confidence: "Mixed",
    red_flag_count: 1,
  },
];

test("shows an empty state when there is no research at all", () => {
  render(<ResearchDigest entries={[]} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getByText("No research has been logged yet.")).toBeInTheDocument();
});

test("defaults to the most recent date and shows its stocks", () => {
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getByRole("combobox")).toHaveValue("2026-09-10");
  expect(screen.getByText("Reliance Industries")).toBeInTheDocument();
  expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument();
});

test("shows the red-flag count badge only when there are red flags", () => {
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getByText("2 red flags")).toBeInTheDocument();
  expect(screen.queryByText(/0 red flag/)).not.toBeInTheDocument();
});

test("switching the date dropdown shows that day's stocks instead", async () => {
  const user = userEvent.setup();
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={vi.fn()} />);

  await user.selectOptions(screen.getByRole("combobox"), "2026-09-09");

  expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument();
  expect(screen.queryByText("Reliance Industries")).not.toBeInTheDocument();
  expect(screen.getByText("1 red flag")).toBeInTheDocument();
});

test("collapses duplicate same-day entries for a stock, keeping the latest", () => {
  const sameDayDuplicate: NewsDigestEntry[] = [
    {
      ticker: "TCS.NS",
      name: "Tata Consultancy Services",
      computed_at: "2026-09-10T08:05:00Z",
      confidence: "Corroborated",
      red_flag_count: 0,
    },
    {
      ticker: "TCS.NS",
      name: "Tata Consultancy Services",
      computed_at: "2026-09-10T07:00:00Z",
      confidence: "Mixed",
      red_flag_count: 1,
    },
  ];
  render(<ResearchDigest entries={sameDayDuplicate} error={null} onSelectTicker={vi.fn()} />);
  expect(screen.getAllByText("Tata Consultancy Services")).toHaveLength(1);
  expect(screen.getByText("Corroborated")).toBeInTheDocument();
});

test("tapping a row calls onSelectTicker with its ticker", async () => {
  const user = userEvent.setup();
  const onSelectTicker = vi.fn();
  render(<ResearchDigest entries={entries} error={null} onSelectTicker={onSelectTicker} />);
  await user.click(screen.getByText("Reliance Industries"));
  expect(onSelectTicker).toHaveBeenCalledWith("RELIANCE.NS");
});

test("shows an error alert when fetching failed", () => {
  render(
    <ResearchDigest entries={null} error="failed to fetch news digest: 500" onSelectTicker={vi.fn()} />
  );
  expect(screen.getByText("failed to fetch news digest: 500")).toBeInTheDocument();
});
