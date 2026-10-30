"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Braces,
  Brain,
  ClipboardType,
  Filter,
  Scale,
  Sparkles,
  Split,
} from "lucide-react";
import { cn } from "@/lib/utils";

const STAGES = [
  {
    icon: ClipboardType,
    title: "Input",
    detail: "The raw review text, exactly as the reviewer wrote it — including typos, CAPS and punctuation.",
  },
  {
    icon: Filter,
    title: "Clean",
    detail: "Lower-casing, stripping URLs and HTML, normalizing whitespace. The same clean_text() used at training time.",
  },
  {
    icon: Split,
    title: "Tokenize",
    detail: "The text is split into individual words (tokens) the models can count and weigh.",
  },
  {
    icon: Braces,
    title: "Lemmatize",
    detail: "Word forms collapse to their base: “loved”, “loving” and “loves” all become “love”.",
  },
  {
    icon: Sparkles,
    title: "TF-IDF + Sentiment",
    detail: "Each token becomes a weighted number (TF-IDF), joined by VADER sentiment scores and style signals.",
  },
  {
    icon: Brain,
    title: "Model",
    detail: "Naive Bayes or SVM multiplies the evidence together and outputs a probability of “fake”.",
  },
  {
    icon: Scale,
    title: "Verdict",
    detail: "Probability ≥ 50% is flagged fake, with the top contributing tokens shown as evidence.",
  },
];

/** Pipeline nodes joined by animated flowing dashed lines; hover for explanations. */
export function PipelineVisual() {
  const [active, setActive] = useState<number | null>(null);

  return (
    <div>
      <ol className="flex flex-col items-stretch gap-0 md:flex-row md:items-center">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon;
          const isActive = active === i;
          return (
            <li key={stage.title} className="flex flex-col items-center md:flex-1">
              <motion.div
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.08, duration: 0.35 }}
                onMouseEnter={() => setActive(i)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(i)}
                onBlur={() => setActive(null)}
                tabIndex={0}
                role="button"
                aria-label={`${stage.title}: ${stage.detail}`}
                className={cn(
                  "group relative z-10 flex h-16 w-16 shrink-0 cursor-default items-center justify-center rounded-2xl border transition-colors",
                  isActive
                    ? "border-aqua/60 bg-aqua/12 text-aqua shadow-glow-brand"
                    : "border-line/15 bg-line/5 text-dim hover:border-line/30"
                )}
              >
                <Icon className="h-7 w-7" aria-hidden />
                <span className="pointer-events-none absolute -bottom-6 whitespace-nowrap font-mono text-[10px] uppercase tracking-wider text-faint">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </motion.div>
              <p className="mt-10 text-center font-display text-sm font-semibold text-ink">
                {stage.title}
              </p>

              {/* Flowing connector */}
              {i < STAGES.length - 1 && (
                <>
                  {/* Desktop: horizontal */}
                  <svg
                    className="my-2 hidden h-2 w-full md:block"
                    aria-hidden
                    viewBox="0 0 100 8"
                    preserveAspectRatio="none"
                  >
                    <line
                      x1="0"
                      y1="4"
                      x2="100"
                      y2="4"
                      stroke="rgb(var(--line) / 0.3)"
                      strokeWidth="2"
                      strokeDasharray="6 6"
                      className="animate-flow-dash"
                    />
                  </svg>
                  {/* Mobile: vertical */}
                  <svg className="mx-auto my-1 block h-8 w-2 md:hidden" aria-hidden viewBox="0 0 8 32">
                    <line
                      x1="4"
                      y1="0"
                      x2="4"
                      y2="32"
                      stroke="rgb(var(--line) / 0.3)"
                      strokeWidth="2"
                      strokeDasharray="6 6"
                      className="animate-flow-dash"
                    />
                  </svg>
                </>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-6 min-h-[72px]">
        <AnimatePresence mode="wait">
          {active !== null ? (
            <motion.div
              key={active}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="glass px-5 py-4"
              aria-live="polite"
            >
              <span className="font-mono text-[10px] uppercase tracking-wider text-aqua">
                Stage {active + 1} · {STAGES[active].title}
              </span>
              <p className="mt-1 text-sm leading-relaxed text-dim">{STAGES[active].detail}</p>
            </motion.div>
          ) : (
            <motion.p
              key="hint"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-1 pt-6 text-center text-sm text-faint"
            >
              Hover or focus any stage to see what happens there.
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
