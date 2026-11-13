import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("glass p-6", className)} {...props} />;
}

export function CardHeader({
  title,
  subtitle,
  action,
  className,
  as: Heading = "h3",
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
  as?: "h2" | "h3";
}) {
  return (
    <div className={cn("mb-4 flex flex-wrap items-start justify-between gap-3 sm:gap-4", className)}>
      <div className="min-w-0 flex-1">
        <Heading className="font-display text-base font-semibold tracking-tight text-ink">
          {title}
        </Heading>
        {subtitle && <p className="mt-0.5 text-xs text-faint">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
