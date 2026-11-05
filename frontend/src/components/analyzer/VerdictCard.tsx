"use client";

import { motion } from "framer-motion";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import type { PredictionResult } from "@/lib/types";
import { formatPercent } from "@/lib/utils";

export function VerdictCard({ result }: { result: PredictionResult }) {
  const fake = result.verdict === "fake";
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="relative overflow-hidden rounded-card border p-6"
      style={{
        borderColor: fake ? "rgb(var(--fake) / 0.3)" : "rgb(var(--genuine) / 0.3)",
        boxShadow: fake
          ? "0 0 60px -18px rgb(var(--fake) / 0.5), inset 0 0 40px -30px rgb(var(--fake) / 0.4)"
          : "0 0 60px -18px rgb(var(--genuine) / 0.45), inset 0 0 40px -30px rgb(var(--genuine) / 0.35)",
      }}
    >
      {/* Pulse halo on reveal */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-card"
        style={{
          boxShadow: fake
            ? "0 0 80px -10px rgb(var(--fake) / 0.55)"
            : "0 0 80px -10px rgb(var(--genuine) / 0.5)",
        }}
        animate={{ opacity: [0.9, 0.25, 0.55] }}
        transition={{ duration: 2.2, repeat: Infinity, repeatType: "mirror" }}
      />
      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
            Verdict
          </p>
          <h2
            className="mt-1 font-display text-3xl font-bold tracking-tight md:text-4xl"
            style={{ color: fake ? "rgb(var(--fake))" : "rgb(var(--genuine))" }}
          >
            Likely {fake ? "Fake" : "Genuine"}
          </h2>
          <p className="mt-2 text-sm text-dim">
            {result.model_used === "tier1_rules" ? (
              <>
                Auto-flagged by rules at{" "}
                <span className="font-mono font-semibold text-ink">100%</span> — the{" "}
                <span className="font-mono font-semibold text-ink uppercase">model</span>{" "}
                was not consulted
              </>
            ) : (
              <>
                Model confidence{" "}
                <span className="font-mono font-semibold text-ink">
                  {formatPercent(result.confidence)}
                </span>{" "}
                · scored by{" "}
                <span className="font-mono font-semibold text-ink uppercase">
                  {result.model_used}
                </span>{" "}
                in <span className="font-mono text-ink">{result.latency_ms} ms</span>
              </>
            )}
          </p>
        </div>
        <motion.span
          initial={{ scale: 0, rotate: -30 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 18, delay: 0.08 }}
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
          style={{
            background: fake ? "rgb(var(--fake) / 0.14)" : "rgb(var(--genuine) / 0.14)",
            color: fake ? "rgb(var(--fake))" : "rgb(var(--genuine))",
          }}
        >
          {fake ? <ShieldAlert className="h-6 w-6" /> : <ShieldCheck className="h-6 w-6" />}
        </motion.span>
      </div>
    </motion.div>
  );
}
