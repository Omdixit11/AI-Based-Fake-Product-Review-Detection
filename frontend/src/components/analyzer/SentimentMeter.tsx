"use client";

import { motion } from "framer-motion";
import type { Sentiment } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * VADER compound score on a -1..+1 gradient track
 * (coral -> neutral -> mint) with an animated marker.
 */
export function SentimentMeter({ sentiment }: { sentiment: Sentiment }) {
  // Map compound [-1, 1] to percent [4, 96]
  const pct = 4 + ((sentiment.compound + 1) / 2) * 92;

  return (
    <div>
      <div className="flex items-center justify-between text-xs text-faint">
        <span>Negative</span>
        <span>Positive</span>
      </div>
      <div
        className="relative mt-2 h-2.5 rounded-pill"
        style={{
          background:
            "linear-gradient(90deg, rgb(var(--fake) / 0.7), rgb(var(--line) / 0.18) 50%, rgb(var(--genuine) / 0.7))",
        }}
        role="meter"
        aria-valuemin={-1}
        aria-valuemax={1}
        aria-valuenow={sentiment.compound}
        aria-label={`Sentiment compound score ${sentiment.compound}`}
      >
        <motion.span
          initial={{ left: "50%" }}
          animate={{ left: `${pct}%` }}
          transition={{ type: "spring", stiffness: 160, damping: 20 }}
          className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-bg bg-ink shadow-lift"
        />
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 font-mono text-[11px]">
        {(
          [
            ["Compound", sentiment.compound.toFixed(2)],
            ["Positive", sentiment.pos.toFixed(2)],
            ["Neutral", sentiment.neu.toFixed(2)],
            ["Negative", sentiment.neg.toFixed(2)],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded-lg bg-line/5 px-2 py-1.5 text-center">
            <div className={cn("text-sm font-semibold text-ink")}>{value}</div>
            <div className="mt-0.5 text-[10px] uppercase tracking-wide text-faint">
              {label}
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-faint">
        VADER sentiment:{" "}
        <span
          className={cn(
            "font-medium",
            sentiment.label === "Positive" && "text-genuine",
            sentiment.label === "Negative" && "text-fake",
            sentiment.label === "Mixed" && "text-warn"
          )}
        >
          {sentiment.label}
        </span>
      </p>
    </div>
  );
}
