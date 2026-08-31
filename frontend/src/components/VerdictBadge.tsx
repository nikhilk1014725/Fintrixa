import { Badge } from "./ui/badge";
import { toDisplayLabel } from "../lib/verdictDisplay";

const VARIANT_MAP: Record<string, "strong-buy" | "buy" | "hold" | "avoid"> = {
  "Strong Buy": "strong-buy",
  Buy: "buy",
  Hold: "hold",
  Avoid: "avoid",
};

export function VerdictBadge({ label }: { label: string }) {
  return <Badge variant={VARIANT_MAP[label] ?? "neutral"}>{toDisplayLabel(label)}</Badge>;
}
