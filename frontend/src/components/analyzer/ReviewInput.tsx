"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  ChevronRight,
  Eraser,
  ScanSearch,
  SlidersHorizontal,
  Sparkles,
  User,
  Zap,
} from "lucide-react";
import { cn, cleanMetadata, SAMPLE_REVIEWS } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Chip } from "@/components/ui/chip";
import type { ModelChoice, PredictMetadata } from "@/lib/types";
import { ModelSwitch } from "./ModelSwitch";
import { StarRating } from "./StarRating";

const MAX_CHARS = 2000;
const SCAN_STAGES = ["Cleaning text", "Extracting features", "Scoring review"];

/**
 * Left-column input card: textarea, counter, optional rating,
 * model switch, sample chips and the Analyze action (Ctrl+Enter).
 *
 * The collapsed "Advanced" disclosure adds the Phase 3.5 Tier-1 metadata. It is
 * closed by default so the card looks exactly like it did in Phase 3 until the
 * reviewer chooses to open it.
 */
export function ReviewInput({
  value,
  onChange,
  rating,
  onRatingChange,
  model,
  onModelChange,
  metadata,
  onMetadataChange,
  scanning,
  onAnalyze,
}: {
  value: string;
  onChange: (v: string) => void;
  rating: number | undefined;
  onRatingChange: (v: number | undefined) => void;
  model: ModelChoice;
  onModelChange: (v: ModelChoice) => void;
  metadata: PredictMetadata;
  onMetadataChange: (m: PredictMetadata) => void;
  scanning: boolean;
  onAnalyze: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [stage, setStage] = useState(0);
  const [advancedOpen, setAdvancedOpen] = useState(false);

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
  // Only the fields the reviewer actually filled in count as "set".
  const advancedCount = Object.keys(cleanMetadata(metadata) ?? {}).length;

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
              onMetadataChange({});
            }}
            disabled={!value && rating === undefined && advancedCount === 0}
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

      {/* Phase 3.5 — optional Tier-1 metadata, collapsed by default. */}
      <div className="mt-5 rounded-xl border border-line/10 bg-line/4">
        <button
          type="button"
          onClick={() => setAdvancedOpen((o) => !o)}
          aria-expanded={advancedOpen}
          aria-controls="advanced-metadata"
          className={cn(
            "flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors hover:bg-line/6",
            "rounded-xl"
          )}
        >
          <motion.span animate={{ rotate: advancedOpen ? 90 : 0 }} transition={{ duration: 0.18 }} aria-hidden>
            <ChevronRight className="h-4 w-4 text-faint" />
          </motion.span>
          <SlidersHorizontal className="h-3.5 w-3.5 text-faint" aria-hidden />
          <span className="flex-1 font-mono text-[10px] uppercase tracking-wider text-dim">
            Advanced — reviewer context
            {advancedCount > 0 && (
              <span className="ml-2 rounded-pill bg-aqua/12 px-2 py-0.5 text-aqua normal-case tracking-normal">
                {advancedCount} set
              </span>
            )}
          </span>
          <span className="font-mono text-[10px] text-faint">optional</span>
        </button>

        <AnimatePresence initial={false}>
          {advancedOpen && (
            <motion.div
              id="advanced-metadata"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="overflow-hidden"
            >
              <div className="grid gap-3 border-t border-line/10 px-3 py-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1.5">
                  <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-faint">
                    <User className="h-3 w-3" aria-hidden /> Reviewer id
                  </span>
                  <input
                    type="text"
                    value={metadata.user_id ?? ""}
                    onChange={(e) =>
                      onMetadataChange({ ...metadata, user_id: e.target.value.slice(0, 128) })
                    }
                    maxLength={128}
                    disabled={scanning}
                    placeholder="u-1042"
                    className="rounded-lg border border-line/15 bg-bg/60 px-3 py-2 font-mono text-xs text-ink placeholder:text-faint focus:border-aqua/40 focus:outline-none disabled:opacity-60"
                  />
                  <span className="text-[10px] leading-snug text-faint">
                    Lets the server count this reviewer&apos;s submissions in a rolling
                    60-second window.
                  </span>
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-faint">
                    <Zap className="h-3 w-3" aria-hidden /> Reviews in the last minute
                  </span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={0}
                    max={10000}
                    step={1}
                    value={metadata.reviews_last_minute ?? ""}
                    onChange={(e) => {
                      const raw = e.target.value;
                      onMetadataChange(
                        raw === ""
                          ? { ...metadata, reviews_last_minute: undefined }
                          : { ...metadata, reviews_last_minute: Number(raw) }
                      );
                    }}
                    disabled={scanning}
                    placeholder="0"
                    className="rounded-lg border border-line/15 bg-bg/60 px-3 py-2 font-mono text-xs text-ink placeholder:text-faint focus:border-aqua/40 focus:outline-none disabled:opacity-60"
                  />
                  <span className="text-[10px] leading-snug text-faint">
                    More than 5 flags the review as spam before the model runs
                    (<span className="font-mono">VELOCITY_EXCEEDED</span>).
                  </span>
                </label>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
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
