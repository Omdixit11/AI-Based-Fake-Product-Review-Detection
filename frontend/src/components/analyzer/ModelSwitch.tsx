"use client";

import { motion } from "framer-motion";
import type { ModelChoice } from "@/lib/types";
import { cn } from "@/lib/utils";
import { pressable } from "@/app/providers";

const OPTIONS: Array<{ value: ModelChoice; label: string; hint: string }> = [
  { value: "best", label: "Best", hint: "auto" },
  { value: "nb", label: "Naive Bayes", hint: "nb" },
  { value: "svm", label: "SVM", hint: "svm" },
];

export function ModelSwitch({
  value,
  onChange,
  disabled = false,
}: {
  value: ModelChoice;
  onChange: (v: ModelChoice) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Model"
      className="inline-flex items-center gap-1 rounded-pill border border-line/15 bg-line/5 p-1"
    >
      {OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={cn(
              pressable,
              "relative rounded-pill px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
              active ? "text-ink" : "text-dim hover:text-ink"
            )}
          >
            {active && (
              <motion.span
                layoutId="model-switch-pill"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
                className="absolute inset-0 rounded-pill bg-line/12 ring-1 ring-aqua/30"
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
