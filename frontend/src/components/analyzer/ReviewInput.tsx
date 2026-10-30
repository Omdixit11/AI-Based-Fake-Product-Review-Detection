"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Eraser, ScanSearch, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Chip } from "@/components/ui/chip";
import type { ModelChoice } from "@/lib/types";
import { ModelSwitch } from "./ModelSwitch";
import { StarRating } from "./StarRating";
import { SAMPLE_REVIEWS } from "@/lib/utils";

const MAX_CHARS = 2000;
const SCAN_STAGES = ["Cleaning text", "Extracting features", "Scoring review"];

/**
 * Left-column input card: textarea, counter, optional rating,
 * model switch, sample chips and the Analyze action (Ctrl+Enter).
 */
export function ReviewInput({
  value,
  onChange,
  rating,
  onRatingChange,
  model,
  onModelChange,
  scanning,
  onAnalyze,
}: {
  value: string;
  onChange: (v: string) => void;
  rating: number | undefined;
  onRatingChange: (v: number | undefined) => void;
  model: ModelChoice;
  onModelChange: (v: ModelChoice) => void;
  scanning: boolean;
  onAnalyze: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [stage, setStage] = useState(0);

  // Listen for the command palette's "load sample" requests.
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { review: string; rating?: number };
      onChange(detail.review);
      onRatingChange(detail.rating);
      textareaRef.current?.focus();
    };
    window.addEventListener("truthlens:load-sample", handler);
    return () => window.removeEventListener("truthlens:load-sample", handler);
  }, [onChange, onRatingChange]);

  // Advance the scanner stage labels while scanning.
  useEffect(() => {
    if (!scanning) {
      setStage(0);
      return;
    }
    const t = window.setInterval(() => setStage((s) => Math.min(s + 1, SCAN_STAGES.length - 1)), 320);
    return () => window.clearInterval(t);
  }, [scanning]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        onAnalyze();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onAnalyze]);

  const chars = value.length;
  const nearLimit = chars > MAX_CHARS * 0.9;

  return (
    <Card className="relative overflow-hidden">
      <CardHeader
        title="Review scanner"
        subtitle="Paste a product review — we do the forensics."
        action={
          <button
            type="button"
            onClick={() => {
              onChange("");
              onRatingChange(undefined);
            }}
            disabled={!value && rating === undefined}
            className="inline-flex items-center gap-1.5 rounded-pill border border-line/15 px-3 py-1.5 text-xs text-dim transition-colors hover:text-ink disabled:opacity-40"
          >
            <Eraser className="h-3.5 w-3.5" /> Clear
          </button>
        }
      />

      <div className="relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value.slice(0, MAX_CHARS))}
          rows={9}
          placeholder={"e.g. “Absolutely AMAZING!!! Best purchase ever, buy it NOW!!!” …or an honest one."}
          aria-label="Product review text"
          disabled={scanning}
          className={cn(
            "w-full resize-y rounded-2xl border border-line/15 bg-bg/60 p-4 text-[15px] leading-relaxed text-ink",
            "placeholder:text-faint focus:border-aqua/40 focus:outline-none",
            "disabled:opacity-60"
          )}
        />
        {/* Scanner sweep + staged labels */}
        <AnimatePresence>
          {scanning && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl"
              aria-hidden
            >
              <div className="scanline" />
              <div className="absolute bottom-3 left-4 flex items-center gap-3">
                {SCAN_STAGES.map((s, i) => (
                  <span key={s} className="flex items-center gap-1.5 font-mono text-[11px]">
                    {i < stage ? (
                      <Check className="h-3 w-3 text-genuine" />
                    ) : i === stage ? (
                      <motion.span
                        className="h-2 w-2 rounded-full bg-aqua"
                        animate={{ opacity: [1, 0.3, 1] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                      />
                    ) : (
                      <span className="h-2 w-2 rounded-full bg-line/25" />
                    )}
                    <span className={i <= stage ? "text-ink" : "text-faint"}>{s}</span>
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-2 flex items-center justify-between font-mono text-[11px]">
        <span className="text-faint">
          <kbd className="rounded border border-line/15 bg-line/5 px-1.5 py-0.5">Ctrl</kbd>+
          <kbd className="rounded border border-line/15 bg-line/5 px-1.5 py-0.5">Enter</kbd> to scan
        </span>
        <span className={cn(nearLimit ? "text-warn" : "text-faint")}>
          {chars.toLocaleString()} / {MAX_CHARS.toLocaleString()}
        </span>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
            Reviewer rating <span className="normal-case">(optional)</span>
          </span>
          <StarRating value={rating} onChange={onRatingChange} />
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-faint">Model</span>
          <ModelSwitch value={model} onChange={onModelChange} disabled={scanning} />
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-faint">
          <Sparkles className="h-3 w-3" /> Try a sample
        </span>
        {SAMPLE_REVIEWS.map((s) => (
          <Chip key={s.label} onClick={() => { onChange(s.review); onRatingChange(s.rating); }}>
            {s.label}
          </Chip>
        ))}
      </div>

      <Button
        onClick={onAnalyze}
        loading={scanning}
        disabled={!value.trim() || scanning}
        size="lg"
        className="mt-6 w-full"
      >
        <ScanSearch className="h-5 w-5" aria-hidden />
        {scanning ? "Scanning…" : "Analyze review"}
      </Button>
    </Card>
  );
}
