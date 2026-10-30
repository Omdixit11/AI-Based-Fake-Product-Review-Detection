"use client";

import { motion } from "framer-motion";
import { ArrowDownLeft, ArrowUpRight } from "lucide-react";
import type { TokenScore } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Top contributing tokens, with a bar showing direction and magnitude. */
export function TopTokens({ tokens, limit = 5 }: { tokens: TokenScore[]; limit?: number }) {
  const top = tokens.slice(0, limit);
  if (top.length === 0) {
    return <p className="text-sm text-faint">No significant tokens found.</p>;
  }
  const max = Math.max(...top.map((t) => Math.abs(t.score)), 0.1);
  return (
    <ul className="space-y-2.5">
      {top.map((t, i) => {
        const fake = t.direction === "fake";
        const width = Math.max(8, (Math.abs(t.score) / max) * 100);
        return (
          <motion.li
            key={t.token}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 + i * 0.07, duration: 0.3 }}
            className="flex items-center gap-3"
          >
            <span className="w-24 shrink-0 truncate font-mono text-xs text-ink" title={t.token}>
              {t.token}
            </span>
            <div className="relative h-4 flex-1 overflow-hidden rounded-pill bg-line/6">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${width}%` }}
                transition={{ delay: 0.2 + i * 0.07, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                className={cn(
                  "absolute inset-y-0 left-0 rounded-pill",
                  fake ? "bg-fake/70" : "bg-genuine/70"
                )}
              />
            </div>
            <span
              className={cn(
                "flex w-16 shrink-0 items-center justify-end gap-1 font-mono text-[11px]",
                fake ? "text-fake" : "text-genuine"
              )}
            >
              {fake ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownLeft className="h-3 w-3" />}
              {t.score > 0 ? "+" : ""}
              {t.score.toFixed(2)}
            </span>
          </motion.li>
        );
      })}
    </ul>
  );
}
