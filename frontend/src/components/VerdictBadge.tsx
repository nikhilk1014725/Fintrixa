const LABEL_COLOR: Record<string, string> = {
  "Strong Buy": "var(--signal-strong-buy)",
  Buy: "var(--signal-buy)",
  Hold: "var(--signal-hold)",
  Avoid: "var(--signal-avoid)",
};

export function VerdictBadge({ label }: { label: string }) {
  const color = LABEL_COLOR[label] ?? "var(--ink-400)";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 600,
        color,
        backgroundColor: `${color}26`,
        border: `1px solid ${color}`,
      }}
    >
      {label}
    </span>
  );
}
