"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, ScanSearch } from "lucide-react";
import { api } from "@/lib/api";
import type { PredictionResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SAMPLE_REVIEWS } from "@/lib/utils";
import { requestSampleReview } from "@/components/layout/command-palette";
import { pressable } from "@/app/providers";

/** Landing hero's live mini analyzer — runs a real (mock) prediction inline. */
export function MiniAnalyzer() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!text.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.predict({ review: text.trim(), model: "best" });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setBusy(false);
    }
  };

  const fake = result?.verdict === "fake";

  return (
    <div className="glass w-full max-w-xl p-5">
      <label htmlFor="mini-review" className="mb-2 block font-mono text-[10px] uppercase tracking-wider text-faint">
        Try it now — paste any product review
      </label>
      <div className="relative">
        <textarea
          id="mini-review"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, 600))}
          rows={3}
          placeholder="“Absolutely AMAZING!!! Best purchase ever!!!”"
          disabled={busy}
          className="w-full resize-none rounded-2xl border border-line/15 bg-bg/60 p-4 text-sm leading-relaxed text-ink placeholder:text-faint focus:border-aqua/40 focus:outline-none disabled:opacity-60"
        />
        {busy && <div className="scanline rounded-2xl" aria-hidden />}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {SAMPLE_REVIEWS.map((s) => (
          <button
            key={s.label}
            type="button"
            onClick={() => setText(s.review)}
            className="rounded-pill border border-line/15 px-3 py-1 text-[11px] text-dim transition-colors hover:border-aqua/40 hover:text-ink"
          >
            {s.label}
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={run}
        disabled={!text.trim() || busy}
        className={cn(
          pressable,
          "mt-4 inline-flex w-full items-center justify-center gap-2 rounded-pill bg-gradient-to-r from-brand to-aqua px-5 py-3 font-display text-sm font-semibold text-white shadow-glow-brand hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        )}
      >
        <ScanSearch className="h-4 w-4" aria-hidden />
        {busy ? "Scanning…" : "Run a quick scan"}
      </button>

      {error && <p className="mt-3 text-sm text-fake">{error}</p>}

      {result && !busy && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="mt-4 rounded-2xl border p-4"
          style={{
            borderColor: fake ? "rgb(var(--fake) / 0.3)" : "rgb(var(--genuine) / 0.3)",
            background: fake ? "rgb(var(--fake) / 0.06)" : "rgb(var(--genuine) / 0.06)",
          }}
          aria-live="polite"
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-display text-lg font-bold" style={{ color: fake ? "rgb(var(--fake))" : "rgb(var(--genuine))" }}>
                Likely {result.verdict}
              </p>
              <p className="mt-0.5 text-xs text-faint">
                {Math.round(result.fake_probability * 100)}% fake probability · {result.sentiment.label.toLowerCase()} sentiment
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                router.push("/analyze");
                window.setTimeout(() => requestSampleReview(text), 350);
              }}
              className="inline-flex items-center gap-1.5 rounded-pill border border-line/20 px-3.5 py-2 text-xs text-ink transition-colors hover:border-aqua/40"
            >
              Full analysis <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
