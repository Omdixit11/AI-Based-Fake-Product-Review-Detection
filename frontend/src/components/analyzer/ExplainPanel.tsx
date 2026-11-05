"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Sigma, Sparkles, TriangleAlert } from "lucide-react";
import { api } from "@/lib/api";
import { ApiRequestError } from "@/lib/types";
import type { ExplainMethod, ExplainResponse, ModelChoice, TokenScore } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/chip";
import { Tooltip } from "@/components/ui/tooltip";

/** Honest, plain-language gloss for each method label the backend can send. */
const METHOD_NOTE: Record<ExplainMethod, string> = {
  "shap-linear":
    "SHAP values from shap.LinearExplainer on the linear SVM (zero background).",
  "linear-coefficients":
    "Same numbers, computed directly as coefficient × TF-IDF — the optional shap package is off or not installed.",
  "naive-bayes-logprob":
    "Log-probability difference, fake vs genuine. Naive Bayes has no SHAP here — this is not SHAP.",
};

const TRIM = /^[^0-9A-Za-z\u00C0-\u024F\u0900-\u097F']+|[^0-9A-Za-z\u00C0-\u024F\u0900-\u097F']+$/g;

/** Surface word (lower-cased) -> the token that explains it. */
function surfaceIndex(resp: ExplainResponse): Map<string, TokenScore> {
  const bySurface = new Map<string, TokenScore>();
  for (const token of resp.tokens) {
    const surfaces = resp.token_map[token.token] ?? [token.token];
    bySurface.set(token.token.toLowerCase(), token);
    for (const surface of surfaces) {
      const key = surface.toLowerCase().replace(TRIM, "");
      if (key && !bySurface.has(key)) bySurface.set(key, token);
    }
  }
  return bySurface;
}

function ExplainText({ review, result }: { review: string; result: ExplainResponse }) {
  const index = surfaceIndex(result);
  const maxAbs = Math.max(0.1, ...result.tokens.map((t) => Math.abs(t.score)));

  return (
    <p className="text-sm leading-7 text-dim">
      {review.split(/(\s+)/).map((part, i) => {
        const key = part.toLowerCase().replace(TRIM, "");
        const hit = key ? index.get(key) : undefined;
        if (!hit) return <span key={i}>{part}</span>;

        const fake = hit.direction === "fake";
        const intensity = Math.min(Math.abs(hit.score) / maxAbs, 1);
        return (
          <Tooltip
            key={i}
            content={
              <span>
                {hit.token} · {hit.score > 0 ? "+" : ""}
                {hit.score.toFixed(4)} → {hit.direction}
              </span>
            }
          >
            <span
              className="cursor-help rounded px-0.5"
              style={{
                background: fake
                  ? `rgb(var(--fake) / ${0.1 + intensity * 0.3})`
                  : `rgb(var(--genuine) / ${0.1 + intensity * 0.26})`,
              }}
            >
              {part}
            </span>
          </Tooltip>
        );
      })}
    </p>
  );
}

/**
 * Phase 3.5 — on-demand explanations.
 *
 * Separate from the prediction itself (its own POST /api/explain call), so a
 * slow explanation never blocks a verdict. The method label is shown exactly as
 * the backend sends it, with a plain-language gloss: a Naive Bayes explanation
 * is never presented as SHAP.
 */
export function ExplainPanel({
  review,
  model,
}: {
  review: string;
  model: ModelChoice;
}) {
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    if (!review.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await api.explain({ review: review.trim(), model }));
    } catch (e) {
      setResult(null);
      setError(
        e instanceof ApiRequestError && e.code === "NOT_FOUND"
          ? "This backend has no /api/explain endpoint — it predates Phase 3.5."
          : e instanceof Error
            ? e.message
            : "Explanation failed."
      );
    } finally {
      setLoading(false);
    }
  }, [review, model, loading]);

  const maxAbs = result ? Math.max(0.05, ...result.tokens.map((t) => Math.abs(t.score))) : 1;

  return (
    <Card>
      <CardHeader
        title="Token attribution"
        subtitle="Ask the model which words it actually used, on demand"
        action={
          <div className="flex items-center gap-2">
            <Button size="sm" variant={result ? "secondary" : "primary"} onClick={run} loading={loading}>
              {result ? <ChevronDown className="h-4 w-4" aria-hidden /> : <Sparkles className="h-4 w-4" aria-hidden />}
              {result ? "Re-explain" : "Explain with SHAP"}
            </Button>
          </div>
        }
      />

      {loading && !result && (
        <div className="flex flex-col gap-3" aria-label="Preparing explanation">
          <Skeleton className="h-16" />
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-5 w-1/2" />
        </div>
      )}

      {error && !loading && (
        <div className="flex items-start gap-3 rounded-xl border border-warn/30 bg-warn/8 px-4 py-3">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warn" aria-hidden />
          <p className="text-sm text-dim">{error}</p>
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-pill border border-brand/30 bg-brand/10 px-3 py-1 font-mono text-[11px] text-ink">
              <Sigma className="h-3.5 w-3.5 text-brand" aria-hidden />
              {result.method}
            </span>
            <span className="font-mono text-[11px] text-faint">
              {result.model_used.toUpperCase()} · base {result.base_value.toFixed(4)} ·{" "}
              {result.latency_ms} ms
            </span>
          </div>

          <p className="text-xs leading-relaxed text-faint">{METHOD_NOTE[result.method]}</p>

          <div className="rounded-xl border border-line/10 bg-line/4 p-4">
            <ExplainText review={review} result={result} />
          </div>

          {result.tokens.length === 0 ? (
            <p className="text-sm text-faint">
              No scored tokens — nothing in this text carries weight for the model.
            </p>
          ) : (
            <ul className="space-y-2">
              {result.tokens.map((t) => {
                const fake = t.direction === "fake";
                const width = Math.max(6, (Math.abs(t.score) / maxAbs) * 100);
                const surfaces = result.token_map[t.token] ?? [];
                return (
                  <li key={t.token} className="flex items-center gap-3">
                    <Tooltip content={surfaces.length ? `in the review: ${surfaces.join(", ")}` : t.token}>
                      <span className="w-24 shrink-0 truncate font-mono text-xs text-ink">{t.token}</span>
                    </Tooltip>
                    <div className="relative h-3.5 flex-1 overflow-hidden rounded-pill bg-line/6">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${width}%` }}
                        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                        className={cn("absolute inset-y-0 left-0 rounded-pill", fake ? "bg-fake/70" : "bg-genuine/70")}
                      />
                    </div>
                    <span className={cn("w-16 shrink-0 text-right font-mono text-[11px]", fake ? "text-fake" : "text-genuine")}>
                      {t.score > 0 ? "+" : ""}
                      {t.score.toFixed(4)}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}

          <div className="flex flex-wrap items-center gap-4 border-t border-line/10 pt-3 font-mono text-[10px] uppercase tracking-wider text-faint">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-fake" /> pushes toward fake
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-genuine" /> pushes toward genuine
            </span>
            <span>base + Σ scores = model decision value</span>
          </div>
        </div>
      )}

      {!result && !loading && !error && (
        <p className="text-sm text-faint">
          Nothing computed yet. The explanation is fetched on click, so it never slows a scan.
        </p>
      )}
    </Card>
  );
}
