"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * Confusion matrix heatmap. Layout is [[TN, FP], [FN, TP]] (positive = fake).
 */
export function ConfusionMatrix({
  matrix,
  title,
}: {
  matrix: [number, number][];
  title: string;
}) {
  const cells: Array<{
    value: number;
    label: string;
    tone: "good" | "bad";
    pos: [number, number];
  }> = [
    { value: matrix[0][0], label: "TN", tone: "good", pos: [0, 0] },
    { value: matrix[0][1], label: "FP", tone: "bad", pos: [0, 1] },
    { value: matrix[1][0], label: "FN", tone: "bad", pos: [1, 0] },
    { value: matrix[1][1], label: "TP", tone: "good", pos: [1, 1] },
  ];
  const max = Math.max(...cells.map((c) => c.value), 1);

  return (
    <figure>
      <figcaption className="mb-3 text-center font-mono text-[10px] uppercase tracking-wider text-faint">
        {title}
      </figcaption>
      <div className="grid grid-cols-2 gap-1.5">
        {cells.map((c, i) => {
          const intensity = Math.min(c.value / max, 1);
          const bg =
            c.tone === "good"
              ? `rgb(var(--genuine) / ${0.08 + intensity * 0.4})`
              : `rgb(var(--fake) / ${0.08 + intensity * 0.4})`;
          return (
            <motion.div
              key={c.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05, duration: 0.25 }}
              className="flex aspect-square flex-col items-center justify-center rounded-xl border"
              style={{
                background: bg,
                borderColor: `rgb(var(--line) / 0.12)`,
              }}
              title={`${c.label} = ${c.value}`}
            >
              <span className="font-mono text-2xl font-bold text-ink">{c.value}</span>
              <span
                className={cn(
                  "mt-1 font-mono text-[10px]",
                  c.tone === "good" ? "text-genuine" : "text-fake"
                )}
              >
                {c.label}
              </span>
            </motion.div>
          );
        })}
      </div>
      <div className="mt-3 flex items-center justify-between font-mono text-[10px] text-faint">
        <span>columns: predicted</span>
        <span>rows: actual</span>
      </div>
    </figure>
  );
}
