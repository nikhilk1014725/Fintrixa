import { cn } from "../../lib/utils";
import type { HTMLAttributes } from "react";

export function Alert({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-lg border border-signal-avoid/40 bg-signal-avoid/10 px-4 py-3 text-sm text-signal-avoid",
        className
      )}
      {...props}
    />
  );
}
