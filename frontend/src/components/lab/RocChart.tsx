"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RocCurve } from "@/lib/types";

/** Dark-friendly Recharts ROC curve with entrance animation and tooltip. */
export function RocChart({
  series,
}: {
  series: Array<{ name: string; curve: RocCurve; color: string; auc: number }>;
}) {
  // Merge all series into rows keyed by point index for the shared chart.
  const points = series[0]?.curve.fpr.map((fpr, i) => {
    const row: Record<string, number | string> = { fpr };
    for (const s of series) {
      row[s.name] = s.curve.tpr[i] ?? s.curve.tpr[s.curve.tpr.length - 1] ?? 0;
    }
    return row;
  }) ?? [];

  const axis = {
    stroke: "rgb(var(--ink-faint))",
    fontSize: 10,
    fontFamily: "var(--font-jetbrains)",
  };

  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={points} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="rgb(var(--line) / 0.08)" strokeDasharray="3 6" />
          <XAxis
            dataKey="fpr"
            type="number"
            domain={[0, 1]}
            tickFormatter={(v: number) => v.toFixed(1)}
            {...axis}
            label={{ value: "False positive rate", position: "insideBottom", offset: -2, fontSize: 10, fill: "rgb(var(--ink-faint))" }}
          />
          <YAxis
            type="number"
            domain={[0, 1]}
            tickFormatter={(v: number) => v.toFixed(1)}
            {...axis}
          />
          <RTooltip
            contentStyle={{
              background: "rgb(var(--bg-elevate))",
              border: "1px solid rgb(var(--line) / 0.15)",
              borderRadius: 12,
              fontSize: 12,
              color: "rgb(var(--ink))",
              fontFamily: "var(--font-jetbrains)",
            }}
            formatter={(value, name) => [Number(value).toFixed(3), String(name)]}
            labelFormatter={(label) => `FPR ${Number(label).toFixed(2)}`}
          />
          {series.map((s) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={s.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
              animationDuration={700}
            />
          ))}
          {/* Diagonal = random baseline */}
          <Line
            type="linear"
            dataKey={() => 0}
            stroke="rgb(var(--line) / 0.35)"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            isAnimationActive={false}
            name="random"
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-2 flex flex-wrap justify-center gap-4">
        {series.map((s) => (
          <span key={s.name} className="flex items-center gap-2 font-mono text-[11px] text-dim">
            <span className="h-2 w-4 rounded-full" style={{ background: s.color }} />
            {s.name} · AUC {s.auc.toFixed(3)}
          </span>
        ))}
      </div>
    </div>
  );
}
