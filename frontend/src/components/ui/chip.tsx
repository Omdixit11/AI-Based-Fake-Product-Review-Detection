"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { pressable } from "@/app/providers";

export function Chip({
  active = false,
  onClick,
  children,
  className,
  title,
}: {
  active?: boolean;
  onClick?: () => void;
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  const Tag = onClick ? "button" : "span";
  return (
    <Tag
      onClick={onClick}
      title={title}
      className={cn(
        onClick && pressable,
        "inline-flex items-center gap-1.5 rounded-pill border px-3 py-1.5 text-xs font-medium transition-colors",
        active
          ? "border-aqua/40 bg-aqua/12 text-aqua"
          : "border-line/15 bg-line/5 text-dim hover:border-line/25 hover:text-ink",
        className
      )}
      {...(onClick ? { type: "button" as const } : {})}
    >
      {children}
    </Tag>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("skeleton", className)} />;
}
