import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";
import type { HTMLAttributes } from "react";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
  {
    variants: {
      variant: {
        "strong-buy": "border-signal-strong-buy/40 bg-signal-strong-buy/15 text-signal-strong-buy",
        buy: "border-signal-buy/40 bg-signal-buy/15 text-signal-buy",
        hold: "border-lavender-300/60 bg-lavender-300/15 text-lavender-700 dark:text-lavender-300",
        avoid: "border-signal-avoid/40 bg-signal-avoid/15 text-signal-avoid",
        neutral: "border-ink-400/30 bg-ink-400/10 text-ink-400",
      },
    },
    defaultVariants: { variant: "neutral" },
  }
);

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
