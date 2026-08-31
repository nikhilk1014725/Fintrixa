const DISPLAY_LABELS: Record<string, string> = {
  "Strong Buy": "Strong Opportunity",
  Buy: "Potential Opportunity",
  Hold: "Worth Watching",
  Avoid: "No Clear Opportunity",
};

export function toDisplayLabel(label: string): string {
  return DISPLAY_LABELS[label] ?? label;
}
