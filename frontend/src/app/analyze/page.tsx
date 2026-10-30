"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { ClipboardCopy, FileText, Gauge, ListChecks, MessageSquareText, Type } from "lucide-react";
import { api } from "@/lib/api";
import type { ModelChoice, PredictionResult } from "@/lib/types";
import { useToast } from "@/app/providers";
import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/chip";
import { ReviewInput } from "@/components/analyzer/ReviewInput";
import { VerdictCard } from "@/components/analyzer/VerdictCard";
import { ConfidenceGauge } from "@/components/analyzer/ConfidenceGauge";
import { SentimentMeter } from "@/components/analyzer/SentimentMeter";
import { HighlightedText } from "@/components/analyzer/HighlightedText";
import { TopTokens } from "@/components/analyzer/TopTokens";
import { FlagList } from "@/components/analyzer/FlagList";

const reveal = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
};

function ResultPanel({
  result,
  review,
  onCopy,
}: {
  result: PredictionResult;
  review: string;
  onCopy: () => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <motion.div {...reveal} transition={{ duration: 0.35 }}>
        <VerdictCard result={result} />
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-2">
        <motion.div {...reveal} transition={{ duration: 0.35, delay: 0.08 }}>
          <Card className="flex h-full items-center justify-center py-8">
            <ConfidenceGauge fakeProbability={result.fake_probability} />
          </Card>
        </motion.div>

        <motion.div {...reveal} transition={{ duration: 0.35, delay: 0.14 }}>
          <Card className="h-full">
            <CardHeader
              title="Sentiment"
              subtitle="VADER polarity profile"
              action={<MessageSquareText className="h-4 w-4 text-faint" aria-hidden />}
            />
            <SentimentMeter sentiment={result.sentiment} />
          </Card>
        </motion.div>
      </div>

      <motion.div {...reveal} transition={{ duration: 0.35, delay: 0.2 }}>
        <Card>
          <CardHeader
            title="Evidence highlights"
            subtitle="Words tinted by how strongly they push the verdict — hover for scores"
            action={<Type className="h-4 w-4 text-faint" aria-hidden />}
          />
          <HighlightedText text={review} tokens={result.tokens} />
        </Card>
      </motion.div>

      <div className="grid gap-4 lg:grid-cols-2">
        <motion.div {...reveal} transition={{ duration: 0.35, delay: 0.26 }}>
          <Card className="h-full">
            <CardHeader
              title="Top contributing tokens"
              subtitle={`${result.model_used.toUpperCase()} feature weights`}
              action={<Gauge className="h-4 w-4 text-faint" aria-hidden />}
            />
            <TopTokens tokens={result.tokens} limit={5} />
          </Card>
        </motion.div>

        <motion.div {...reveal} transition={{ duration: 0.35, delay: 0.3 }}>
          <Card className="h-full">
            <CardHeader
              title="Red flags"
              subtitle="Rule-based signals, independent of the model"
              action={<ListChecks className="h-4 w-4 text-faint" aria-hidden />}
            />
            <FlagList flags={result.flags} />
          </Card>
        </motion.div>
      </div>

      <motion.div {...reveal} transition={{ duration: 0.35, delay: 0.34 }}>
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap gap-x-8 gap-y-3 font-mono text-sm">
              {(
                [
                  ["Words", result.meta.words],
                  ["Exclamations", result.meta.exclamations],
                  ["CAPS words", result.meta.caps_words],
                  ["Analyzed", `${result.latency_ms} ms`],
                ] as const
              ).map(([label, value]) => (
                <div key={label}>
                  <div className="text-lg font-semibold text-ink">{value}</div>
                  <div className="text-[10px] uppercase tracking-wider text-faint">{label}</div>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={onCopy}
              className="inline-flex items-center gap-2 rounded-pill border border-line/15 px-4 py-2 text-sm text-dim transition-all hover:border-aqua/40 hover:text-ink active:scale-[0.97]"
            >
              <ClipboardCopy className="h-4 w-4" aria-hidden /> Copy result
            </button>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}

function EmptyState() {
  return (
    <Card className="flex min-h-[420px] flex-col items-center justify-center gap-4 text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-3xl bg-line/6 text-faint">
        <FileText className="h-8 w-8" aria-hidden />
      </span>
      <div>
        <h3 className="font-display text-lg font-semibold text-ink">No scan yet</h3>
        <p className="mx-auto mt-1 max-w-xs text-sm text-faint">
          Paste a review on the left — or try a sample chip — and the full forensic
          breakdown will appear here.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2 font-mono text-[10px] uppercase tracking-wider text-faint">
        <span className="rounded-pill border border-line/15 px-2.5 py-1">Verdict</span>
        <span className="rounded-pill border border-line/15 px-2.5 py-1">Gauge</span>
        <span className="rounded-pill border border-line/15 px-2.5 py-1">Sentiment</span>
        <span className="rounded-pill border border-line/15 px-2.5 py-1">Highlights</span>
        <span className="rounded-pill border border-line/15 px-2.5 py-1">Tokens</span>
        <span className="rounded-pill border border-line/15 px-2.5 py-1">Flags</span>
      </div>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-label="Analyzing review">
      <Skeleton className="h-36" />
      <div className="grid gap-4 sm:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
      <Skeleton className="h-40" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-56" />
        <Skeleton className="h-56" />
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  const [review, setReview] = useState("");
  const [rating, setRating] = useState<number | undefined>(undefined);
  const [model, setModel] = useState<ModelChoice>("best");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const analyze = useCallback(async () => {
    if (!review.trim() || scanning) return;
    setScanning(true);
    setError(null);
    try {
      const res = await api.predict({ review: review.trim(), rating, model });
      setResult(res);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Analysis failed.";
      setError(message);
      toast("error", message);
    } finally {
      setScanning(false);
    }
  }, [review, rating, model, scanning, toast]);

  const copyResult = useCallback(async () => {
    if (!result) return;
    const text = [
      `TruthLens verdict: Likely ${result.verdict === "fake" ? "FAKE" : "GENUINE"} review`,
      `Fake probability: ${(result.fake_probability * 100).toFixed(0)}% (confidence ${(result.confidence * 100).toFixed(0)}%)`,
      `Model: ${result.model_used.toUpperCase()} · Sentiment: ${result.sentiment.label} (${result.sentiment.compound})`,
      `Red flags: ${result.flags.length ? result.flags.map((f) => f.label).join("; ") : "none"}`,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      toast("success", "Result copied to clipboard.");
    } catch {
      toast("error", "Clipboard is not available in this browser.");
    }
  }, [result, toast]);

  return (
    <div className="mx-auto w-full max-w-shell px-4 pb-16">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
          Analyze a review
        </h1>
        <p className="mt-2 max-w-xl text-sm text-dim">
          One review, fully dissected: verdict, confidence, sentiment, the words that
          decided it, and every red flag.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <ReviewInput
          value={review}
          onChange={setReview}
          rating={rating}
          onRatingChange={setRating}
          model={model}
          onModelChange={setModel}
          scanning={scanning}
          onAnalyze={analyze}
        />

        <div aria-live="polite">
          {scanning && !result && <LoadingSkeleton />}
          {error && !scanning && !result && (
            <Card className="border-fake/30">
              <h3 className="font-display text-lg font-semibold text-fake">Scan failed</h3>
              <p className="mt-1 text-sm text-dim">{error}</p>
              <ButtonRetry onRetry={analyze} />
            </Card>
          )}
          {!scanning && result && (
            <ResultPanel result={result} review={review} onCopy={copyResult} />
          )}
          {!scanning && !result && !error && <EmptyState />}
        </div>
      </div>
    </div>
  );
}

function ButtonRetry({ onRetry }: { onRetry: () => void }) {
  return (
    <button
      type="button"
      onClick={onRetry}
      className="mt-4 rounded-pill border border-line/20 px-4 py-2 text-sm text-ink transition-colors hover:border-aqua/40"
    >
      Try again
    </button>
  );
}
