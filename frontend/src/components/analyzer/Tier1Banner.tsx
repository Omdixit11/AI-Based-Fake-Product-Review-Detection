"use client";

import { motion } from "framer-motion";
import { Ban, ShieldOff } from "lucide-react";
import type { Severity, Tier1Block, Tier1Rule } from "@/lib/types";
import { cn } from "@/lib/utils";

const severityDot: Record<Severity, string> = {
  high: "bg-fake",
  medium: "bg-warn",
  low: "bg-aqua",
};

/**
 * Phase 3.5 — Tier-1 banner.
 *
 * Rendered only when `tier1.triggered` is true, i.e. a HARD rule decided the
 * review and the ML model was never consulted. Soft signals ride along as
 * chips because they are informative but never decide anything.
 *
 * The wording matters: `fake_probability: 1.0` on a flagged review is a rule
 * decision, not a model score, and saying so here is the honest thing to do.
 */
export function Tier1Banner({ tier1 }: { tier1?: Tier1Block }) {
  if (!tier1?.triggered) return null;

  const hard: Tier1Rule[] = tier1.rules.filter((r) => r.kind === "hard");
  const soft: Tier1Rule[] = tier1.rules.filter((r) => r.kind === "soft");

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      aria-label="Flagged by Tier-1 rules"
      className="rounded-card border border-fake/30 bg-fake/8 p-5"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-fake/14 text-fake">
          <ShieldOff className="h-5 w-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-sm font-semibold tracking-tight text-ink">
            Flagged by rules — the model was skipped
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-dim">
            A Tier-1 hard rule matched before any classifier ran, so this verdict is a
            <span className="text-ink"> rule decision</span>, not a model probability.
            The 100% figure means “auto-flagged”, not “certainly fake”.
          </p>

          <ul className="mt-3 space-y-1.5">
            {hard.map((rule) => (
              <li key={rule.code} className="flex items-center gap-2.5 text-sm text-ink">
                <Ban className="h-3.5 w-3.5 shrink-0 text-fake" aria-hidden />
                <span className="min-w-0 flex-1 truncate">{rule.label}</span>
                <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
                  {rule.code}
                </span>
              </li>
            ))}
          </ul>

          {soft.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
                Also noted
              </span>
              {soft.map((rule) => (
                <span
                  key={rule.code}
                  title={`${rule.label} · soft signal — reported only, never changes the verdict`}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-pill border border-line/15 bg-line/5 px-2.5 py-1 text-[11px] text-dim"
                  )}
                >
                  <span className={cn("h-1.5 w-1.5 rounded-full", severityDot[rule.severity])} />
                  {rule.label}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.section>
  );
}
