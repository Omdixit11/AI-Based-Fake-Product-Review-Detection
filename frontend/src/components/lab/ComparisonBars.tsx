"use client";

import { motion } from "framer-motion";
import type { ModelMetrics } from "@/lib/types";

const GROUPS: Array<{ key: keyof ModelMetrics; label: string }> = [
  { key: "accuracy", label: "Accuracy" },
  { key: "precision", label: "Precision" },
  { key: "recall", label: "Recall" },
  { key: "f1", label: "F1" },
  { key: "roc_auc", label: "ROC-AUC" },
];

/** Side-by-side NB vs SVM comparison bars for one metric family. */
export function ComparisonBars({
  nb,
  svm,
}: {
  nb: ModelMetrics;
  svm: ModelMetrics;
}) {
  return (
    <div className="space-y-5">
      {GROUPS.map((g, gi) => {
        const nbVal = nb[g.key] as number;
        const svmVal = svm[g.key] as number;
        return (
          <div key={g.key}>
            <div className="mb-2 flex items-baseline justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
                {g.label}
              </span>
              <span className="font-mono text-xs text-dim">
                <span className="text-brand">{nbVal.toFixed(3)}</span>
                {" · "}
                <span className="text-aqua">{svmVal.toFixed(3)}</span>
              </span>
            </div>
            <div className="space-y-1.5">
              {[
                { label: "NB", value: nbVal, cls: "from-brand to-brand/70" },
                { label: "SVM", value: svmVal, cls: "from-aqua to-aqua/70" },
              ].map((row) => (
                <div key={row.label} className="flex items-center gap-3">
                  <span className="w-8 shrink-0 font-mono text-[10px] text-faint">{row.label}</span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-pill bg-line/8">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${row.value * 100}%` }}
                      transition={{ delay: gi * 0.05, duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
                      className={cnBar(row.cls)}
                    />
                  </div>
                  <span className="w-12 shrink-0 text-right font-mono text-[11px] text-dim">
                    {(row.value * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function cnBar(cls: string) {
  return `h-full rounded-pill bg-gradient-to-r ${cls}`;
}
