"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { BatchRow, Verdict } from "@/lib/types";
import { cn, truncate } from "@/lib/utils";
import { Chip } from "@/components/ui/chip";

type SortKey = "row" | "review" | "verdict" | "fake_probability" | "confidence";

const VERDICT_PILL = {
  fake: "bg-fake/12 text-fake ring-1 ring-fake/25",
  genuine: "bg-genuine/12 text-genuine ring-1 ring-genuine/25",
} as const;

export function ResultsTable({ rows }: { rows: BatchRow[] }) {
  const [filter, setFilter] = useState<Verdict | "all">("all");
  const [sortKey, setSortKey] = useState<SortKey>("row");
  const [asc, setAsc] = useState(true);

  const filtered = useMemo(() => {
    const list = filter === "all" ? [...rows] : rows.filter((r) => r.verdict === filter);
    const dir = asc ? 1 : -1;
    list.sort((a, b) => {
      let cmp: number;
      if (sortKey === "review") cmp = a.review.localeCompare(b.review);
      else if (sortKey === "verdict") cmp = a.verdict.localeCompare(b.verdict);
      else cmp = (a[sortKey] as number) - (b[sortKey] as number);
      return cmp * dir;
    });
    return list;
  }, [rows, filter, sortKey, asc]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setAsc((a) => !a);
    else {
      setSortKey(key);
      setAsc(true);
    }
  };

  const SortHeader = ({ label, k, className }: { label: string; k: SortKey; className?: string }) => (
    <th
      scope="col"
      className={cn("px-4 py-3 text-left font-medium", className)}
      aria-sort={sortKey === k ? (asc ? "ascending" : "descending") : "none"}
    >
      <button
        type="button"
        onClick={() => toggleSort(k)}
        className={cn(
          "inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider transition-colors",
          sortKey === k ? "text-ink" : "text-faint hover:text-dim"
        )}
      >
        {label}
        {sortKey === k &&
          (asc ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </th>
  );

  return (
    <div className="glass overflow-hidden p-0">
      <div className="flex flex-wrap items-center gap-2 border-b border-line/10 px-5 py-4">
        <span className="font-display text-sm font-semibold text-ink">Results</span>
        <span className="font-mono text-[11px] text-faint">
          {filtered.length.toLocaleString()} of {rows.length.toLocaleString()} rows
        </span>
        <div className="ml-auto flex gap-2">
          {(["all", "fake", "genuine"] as const).map((v) => (
            <Chip key={v} active={filter === v} onClick={() => setFilter(v)}>
              {v === "all" ? "All" : v === "fake" ? "Fake only" : "Genuine only"}
            </Chip>
          ))}
        </div>
      </div>

      <div className="max-h-[520px] overflow-auto">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-elevate/95 backdrop-blur">
            <tr className="border-b border-line/10">
              <SortHeader label="#" k="row" />
              <th scope="col" className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-wider text-faint">
                Review
              </th>
              <SortHeader label="Verdict" k="verdict" />
              <SortHeader label="Fake prob" k="fake_probability" />
              <SortHeader label="Conf" k="confidence" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => (
              <motion.tr
                key={r.row}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: Math.min(i * 0.02, 0.4), duration: 0.25 }}
                className="border-b border-line/6 transition-colors hover:bg-line/4"
              >
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-faint">
                  {r.row}
                  {r.rating !== undefined && (
                    <span className="ml-1 text-warn" title={`${r.rating} star rating`}>
                      {"★".repeat(r.rating)}
                    </span>
                  )}
                </td>
                <td className="max-w-[420px] px-4 py-3 text-dim" title={r.review}>
                  {truncate(r.review, 96)}
                </td>
                <td className="px-4 py-3">
                  <span className={cn("inline-flex rounded-pill px-2.5 py-0.5 text-xs font-medium", VERDICT_PILL[r.verdict])}>
                    {r.verdict}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs">
                  <span className="inline-flex items-center gap-2">
                    <span className="h-1.5 w-10 overflow-hidden rounded-pill bg-line/10">
                      <span
                        className={cn("block h-full rounded-pill", r.verdict === "fake" ? "bg-fake" : "bg-genuine")}
                        style={{ width: `${r.fake_probability * 100}%` }}
                      />
                    </span>
                    {(r.fake_probability * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-dim">
                  {(r.confidence * 100).toFixed(0)}%
                </td>
              </motion.tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-faint">
                  No rows match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
