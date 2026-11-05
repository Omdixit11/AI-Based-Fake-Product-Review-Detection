"use client";

import { motion } from "framer-motion";
import { Smile } from "lucide-react";
import type { SarcasmBlock } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Phase 3.5 — sarcasm badge.
 *
 * Shown only when `sarcasm.suspected`. It is deliberately amber (warn), not
 * red: the heuristic spotted a positive opening against a negative outcome and
 * is asking a human to look twice. It does NOT mean the review is fake, and the
 * copy says so, because that is the whole point of feature 2.
 */
export function SarcasmBadge({ sarcasm }: { sarcasm?: SarcasmBlock }) {
  if (!sarcasm?.suspected) return null;

  const high = sarcasm.risk_level === "high";
  const cues = [
    ...(sarcasm.positive_cues ?? []).map((c) => ({ text: c, kind: "pos" as const })),
    ...(sarcasm.negative_cues ?? []).map((c) => ({ text: c, kind: "neg" as const })),
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: 0.12 }}
      className={cn(
        "flex items-start gap-3 rounded-card border px-4 py-3",
        high ? "border-warn/35 bg-warn/8" : "border-line/15 bg-line/4"
      )}
    >
      <span
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          high ? "bg-warn/16 text-warn" : "bg-line/8 text-dim"
        )}
        aria-hidden
      >
        <Smile className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <h3 className="font-display text-sm font-semibold tracking-tight text-ink">
            Possible sarcasm — needs human review
          </h3>
          <span className="font-mono text-[10px] uppercase tracking-wider text-warn">
            contrast {sarcasm.score.toFixed(2)}
            {sarcasm.risk_level ? ` · ${sarcasm.risk_level}` : ""}
          </span>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-dim">
          Positive opening against a negative outcome. This is a rule-based risk flag
          only — the verdict and the probability above were scored by the model and
          were not changed by it.
        </p>
        {cues.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {cues.map((cue, i) => (
              <span
                key={`${cue.kind}-${cue.text}-${i}`}
                className={cn(
                  "rounded-pill border px-2 py-0.5 font-mono text-[11px]",
                  cue.kind === "pos"
                    ? "border-genuine/25 bg-genuine/8 text-genuine"
                    : "border-fake/25 bg-fake/8 text-fake"
                )}
              >
                {cue.text}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
