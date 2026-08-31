import { cn } from "../../lib/utils";
import type { HTMLAttributes } from "react";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-lavender-100 dark:bg-lavender-900/30", className)} {...props} />;
}
