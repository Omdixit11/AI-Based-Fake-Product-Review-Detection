"use client";

import { motion } from "framer-motion";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as RTooltip } from "recharts";
import { ShieldAlert, ShieldCheck, Target, TrendingUp } from "lucide-react";
import type { BatchSummary } from "@/lib/types";

export function SummaryStats({ summary }: { summary: BatchSummary }) {
  const genuine = summary.total - summary.fake_count;
  const data = [
    { name: "Fake", value: summary.fake_count, color: "rgb(var(--fake))" },
    { name: "Genuine", value: genuine, color: "rgb(var(--genuine))" },
  ];

  const cards = [
    {
      label: "Reviews scanned",
      value: summary.total.toLocaleString(),
      icon: <Target className="h-4 w-4 text-faint" />,
    },
    {
      label: "Fake detected",
      value: summary.fake_count.toLocaleString(),
      icon: <ShieldAlert className="h-4 w-4 text-fake" />,
    },
    {
      label: "Genuine",
      value: genuine.toLocaleString(),
      icon: <ShieldCheck className="h-4 w-4 text-genuine" />,
    },
    {
      label: "Avg confidence",
      value: `${Math.round(summary.avg_confidence * 100)}%`,
      icon: <TrendingUp className="h-4 w-4 text-aqua" />,
    },
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.35 }}
        className="glass flex items-center justify-center p-6"
      >
        <div className="relative h-44 w-44">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                innerRadius="66%"
                outerRadius="98%"
                paddingAngle={3}
                startAngle={90}
                endAngle={-270}
                stroke="none"
              >
                <Cell fill={data[0].color} />
                <Cell fill={data[1].color} />
              </Pie>
              <RTooltip
                contentStyle={{
                  background: "rgb(var(--bg-elevate))",
                  border: "1px solid rgb(var(--line) / 0.15)",
                  borderRadius: 12,
                  fontSize: 12,
                  color: "rgb(var(--ink))",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-3xl font-bold text-ink">
              {summary.fake_percent.toFixed(1)}%
            </span>
            <span className="text-[10px] uppercase tracking-wider text-faint">fake</span>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-2 gap-4">
        {cards.map((c, i) => (
          <motion.div
            key={c.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.06 * i, duration: 0.3 }}
            className="glass flex flex-col justify-between p-5"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
                {c.label}
              </span>
              {c.icon}
            </div>
            <span className="mt-3 font-mono text-3xl font-bold text-ink">{c.value}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
