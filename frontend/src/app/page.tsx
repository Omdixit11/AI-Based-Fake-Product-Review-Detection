"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  FileSpreadsheet,
  History,
  Layers,
  ScanSearch,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import type { MetricsResponse } from "@/lib/types";
import { MiniAnalyzer } from "@/components/landing/MiniAnalyzer";
import { CountUp } from "@/components/landing/StatCounters";
import { pressable } from "@/app/providers";
import { formatNumber } from "@/lib/utils";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Single-review forensics",
    body: "Verdict, confidence gauge, sentiment profile, red flags and the exact words that tipped the model — for any review you paste.",
    span: "sm:col-span-2",
    accent: true,
  },
  {
    icon: FileSpreadsheet,
    title: "Batch sweeps",
    body: "Drop a CSV of up to 5000 reviews, get a fake/genuine breakdown with donut, table and CSV export.",
    span: "",
  },
  {
    icon: Layers,
    title: "Model Lab",
    body: "Accuracy, F1, ROC curves and confusion matrices — with a TF-IDF vs TF-IDF + sentiment toggle.",
    span: "",
  },
  {
    icon: History,
    title: "Full audit trail",
    body: "Every scan is recorded with its evidence. Search it, filter it, delete it whenever you want.",
    span: "",
  },
  {
    icon: ShieldCheck,
    title: "Explainable by design",
    body: "Classical ML chosen on purpose: every verdict can show its work. No black-box vibes, no hallucinated reasoning.",
    span: "sm:col-span-2",
  },
];

export default function LandingPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);

  useEffect(() => {
    api
      .getMetrics()
      .then(setMetrics)
      .catch(() => setMetrics(null));
  }, []);

  const best = metrics?.models[metrics.best_model]?.tfidf_sentiment;

  return (
    <div className="mx-auto w-full max-w-shell px-4 pb-16">
      {/* ---------------- Hero ---------------- */}
      <section className="grid items-center gap-10 py-8 lg:grid-cols-2 lg:py-16">
        <div>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="inline-flex items-center gap-2 rounded-pill border border-line/15 bg-line/5 px-3.5 py-1.5 font-mono text-[11px] uppercase tracking-[0.18em] text-dim"
          >
            <Sparkles className="h-3.5 w-3.5 text-aqua" aria-hidden />
            Fake review detection, explained
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.06 }}
            className="mt-5 font-display text-4xl font-bold leading-[1.05] tracking-tight text-ink sm:text-5xl lg:text-6xl"
          >
            Every review has a{" "}
            <span className="relative whitespace-nowrap">
              <span className="text-gradient">fingerprint</span>
              <motion.span
                className="absolute -bottom-1 left-0 h-[3px] w-full rounded-full bg-gradient-to-r from-brand to-aqua"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.6, delay: 0.5 }}
                style={{ originX: 0 }}
                aria-hidden
              />
            </span>
            . TruthLens reads it.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.14 }}
            className="mt-5 max-w-lg text-base leading-relaxed text-dim"
          >
            Paste any product review and get a forensic verdict — fake or genuine —
            backed by TF-IDF evidence, sentiment analysis and two battle-tested
            classical models. You see exactly why it decided what it decided.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.2 }}
            className="mt-8 flex flex-wrap gap-3"
          >
            <Link
              href="/analyze"
              className={`${pressable} inline-flex h-12 items-center gap-2 rounded-pill bg-gradient-to-r from-brand to-aqua px-6 font-display text-base font-semibold text-white shadow-glow-brand hover:brightness-110`}
            >
              Scan your first review
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <Link
              href="/how-it-works"
              className={`${pressable} inline-flex h-12 items-center rounded-pill border border-line/20 px-6 font-display text-base font-semibold text-dim transition-colors hover:border-aqua/40 hover:text-ink`}
            >
              See how it works
            </Link>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="flex justify-center lg:justify-end"
        >
          <MiniAnalyzer />
        </motion.div>
      </section>

      {/* ---------------- Stat counters ---------------- */}
      <section aria-label="Model statistics" className="border-y border-line/10 py-10">
        <div className="grid grid-cols-2 gap-6 text-center md:grid-cols-4">
          {[
            {
              value: best ? best.accuracy : 0.909,
              decimals: 1,
              suffix: "%",
              label: "Accuracy",
              hint: best ? `${metrics?.best_model.toUpperCase()} on the test set` : "SVM on the test set",
            },
            {
              value: best ? best.f1 : 0.875,
              decimals: 1,
              suffix: "%",
              label: "F1 score",
              hint: "harmonic mean of precision and recall",
            },
            {
              value: metrics?.dataset.size ?? 1600,
              decimals: 0,
              suffix: "",
              label: "Reviews trained on",
              hint: "balanced fake/genuine corpus",
            },
            {
              value: 2,
              decimals: 0,
              suffix: "",
              label: "Models compared",
              hint: "Naive Bayes and SVM",
            },
          ].map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.07, duration: 0.35 }}
            >
              <div className="text-4xl font-bold tracking-tight text-ink md:text-5xl">
                <CountUp
                  value={s.value}
                  decimals={s.decimals}
                  suffix={s.suffix}
                />
              </div>
              <div className="mt-1.5 font-mono text-[10px] uppercase tracking-wider text-dim">
                {s.label}
              </div>
              <div className="mt-0.5 text-[11px] text-faint">{s.hint}</div>
            </motion.div>
          ))}
        </div>
        {metrics && (
          <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-wider text-faint">
            {metrics.dataset.name} · {formatNumber(metrics.dataset.size)} reviews ·{" "}
            {metrics.best_model.toUpperCase()} selected as best model
          </p>
        )}
      </section>

      {/* ---------------- Features bento ---------------- */}
      <section className="py-16">
        <div className="mb-8 text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight text-ink">
            A full forensic workbench
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-dim">
            Not a toy demo — the complete toolkit for auditing review trust at any scale.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.06, duration: 0.35 }}
                className={`glass group relative overflow-hidden p-6 ${f.span}`}
              >
                {f.accent && (
                  <div
                    aria-hidden
                    className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-gradient-to-br from-brand/20 to-aqua/20 blur-2xl transition-opacity duration-300 group-hover:opacity-100"
                  />
                )}
                <span className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand/15 to-aqua/15 text-aqua">
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                <h3 className="relative mt-4 font-display text-lg font-semibold text-ink">
                  {f.title}
                </h3>
                <p className="relative mt-2 text-sm leading-relaxed text-dim">{f.body}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* ---------------- Final CTA ---------------- */}
      <section className="relative overflow-hidden rounded-card border border-line/15 py-16 text-center">
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-br from-brand/10 via-transparent to-aqua/10"
        />
        <div className="relative">
          <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
            Give your product feed a <span className="text-gradient">truth check</span>.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm text-dim">
            Free, instant and explainable. Paste one review or upload five thousand.
          </p>
          <div className="mt-8 flex justify-center">
            <Link
              href="/analyze"
              className={`${pressable} inline-flex h-12 items-center gap-2 rounded-pill bg-gradient-to-r from-brand to-aqua px-7 font-display text-base font-semibold text-white shadow-glow-brand hover:brightness-110`}
            >
              <ScanSearch className="h-5 w-5" aria-hidden />
              Start analyzing
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
