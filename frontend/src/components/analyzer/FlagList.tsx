"use client";

import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Flag } from "lucide-react";
import type { RedFlag, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

const severityStyles: Record<Severity, { dot: string; text: string }> = {
  high: { dot: "bg-fake", text: "text-fake" },
  medium: { dot: "bg-warn", text: "text-warn" },
  low: { dot: "bg-aqua", text: "text-aqua" },
};

export function FlagList({ flags }: { flags: RedFlag[] }) {
  if (flags.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-xl bg-genuine/8 px-4 py-3 text-sm text-genuine ring-1 ring-genuine/20">
        <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />
        No red flags detected in this review.
      </div>
    );
  }
  return (
    <ul className="space-y-2">
      {flags.map((flag, i) => (
        <motion.li
          key={flag.code}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.06, duration: 0.25 }}
          className="flex items-center gap-3 rounded-xl border border-line/10 bg-line/4 px-4 py-2.5"
        >
          <AlertTriangle
            className={cn("h-4 w-4 shrink-0", severityStyles[flag.severity].text)}
            aria-hidden
          />
          <span className="flex-1 text-sm text-ink">{flag.label}</span>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider",
              severityStyles[flag.severity].text
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", severityStyles[flag.severity].dot)} />
            {flag.severity}
          </span>
        </motion.li>
      ))}
      <li className="flex items-center gap-2 pt-1 font-mono text-[10px] uppercase tracking-wider text-faint">
        <Flag className="h-3 w-3" aria-hidden />
        {flags.length} rule-based flag{flags.length === 1 ? "" : "s"} triggered
      </li>
    </ul>
  );
}
