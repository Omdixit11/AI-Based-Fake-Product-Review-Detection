"use client";

import { motion } from "framer-motion";
import { Award, Crosshair, Gauge, Target } from "lucide-react";
import type { ModelMetrics } from "@/lib/types";
import { cn } from "@/lib/utils";

const METRICS: Array<{ key: keyof ModelMetrics; label: string; icon: React.ReactNode }> = [
  { key: "accuracy", label: "Accuracy", icon: <Target className="h-4 w-4" /> },
  { key: "precision", label: "Precision", icon: <Crosshair className="h-4 w-4" /> },
  { key: "recall", label: "Recall", icon: <Gauge className="h-4 w-4" /> },
  { key: "f1", label: "F1 score", icon: <Award className="h-4 w-4" /> },
];

export function MetricCards({
  metrics,
  isBest,
  accent,
}: {
  metrics: ModelMetrics;
  isBest: boolean;
  accent: "brand" | "aqua";
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {METRICS.map((m, i) => (
        <motion.div
          key={m.key}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05, duration: 0.3 }}
          className={cn(
            "rounded-2xl border p-4",
            isBest
              ? accent === "brand"
                ? "border-brand/40 bg-brand/6"
                : "border-aqua/40 bg-aqua/6"
              : "border-line/10 bg-line/4"
          )}
        >
          <div className="flex items-center justify-between text-faint">
            <span className="font-mono text-[10px] uppercase tracking-wider">{m.label}</span>
            {m.icon}
          </div>
          <div className="mt-2 font-mono text-2xl font-bold text-ink">
            {((metrics[m.key] as number) * 100).toFixed(1)}
            <span className="text-sm text-faint">%</span>
          </div>
          <div className="mt-2 h-1 overflow-hidden rounded-pill bg-line/10">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(metrics[m.key] as number) * 100}%` }}
              transition={{ delay: 0.1 + i * 0.05, duration: 0.5 }}
              className={cn(
                "h-full rounded-pill",
                accent === "brand"
                  ? "bg-gradient-to-r from-brand to-aqua"
                  : "bg-gradient-to-r from-aqua to-genuine"
              )}
            />
          </div>
        </motion.div>
      ))}
    </div>
  );
}
