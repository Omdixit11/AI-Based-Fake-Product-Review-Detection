"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Trash2 } from "lucide-react";
import type { HistoryEntry } from "@/lib/types";
import { cn, timeAgo, truncate } from "@/lib/utils";
import { TopTokens } from "@/components/analyzer/TopTokens";

function parseTokens(json: string) {
  try {
    return JSON.parse(json) as { token: string; score: number; direction: "fake" | "genuine" }[];
  } catch {
    return [];
  }
}

function parseFlags(json: string) {
  try {
    return JSON.parse(json) as string[];
  } catch {
    return [];
  }
}

export function HistoryList({
  entries,
  onDelete,
}: {
  entries: HistoryEntry[];
  onDelete: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (entries.length === 0) {
    return (
      <div className="glass flex flex-col items-center justify-center gap-3 py-16 text-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-line/6 font-mono text-2xl text-faint">
          ∅
        </span>
        <p className="text-sm text-faint">
          No analyses match — run a scan on the Analyze page and it will land here.
        </p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {entries.map((entry, i) => {
        const fake = entry.verdict === "fake";
        const open = expanded === entry.id;
        const tokens = open ? parseTokens(entry.tokens_json) : [];
        const flags = parseFlags(entry.flags_json);
        return (
          <motion.li
            key={entry.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.04, 0.3), duration: 0.3 }}
            className="glass overflow-hidden p-0"
          >
            <button
              type="button"
              onClick={() => setExpanded(open ? null : entry.id)}
              aria-expanded={open}
              className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-line/4"
            >
              <span
                className={cn(
                  "inline-flex shrink-0 rounded-pill px-2.5 py-0.5 text-xs font-medium",
                  fake
                    ? "bg-fake/12 text-fake ring-1 ring-fake/25"
                    : "bg-genuine/12 text-genuine ring-1 ring-genuine/25"
                )}
              >
                {entry.verdict}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm text-dim">
                {truncate(entry.review_text, 80)}
              </span>
              <span className="hidden shrink-0 font-mono text-xs text-faint sm:inline">
                {Math.round(entry.fake_probability * 100)}% fake
              </span>
              <span className="hidden shrink-0 font-mono text-xs text-faint md:inline">
                {entry.model_used.toUpperCase()}
              </span>
              <span className="shrink-0 font-mono text-xs text-faint">{timeAgo(entry.created_at)}</span>
              <ChevronDown
                className={cn(
                  "h-4 w-4 shrink-0 text-faint transition-transform",
                  open && "rotate-180"
                )}
                aria-hidden
              />
            </button>

            <AnimatePresence initial={false}>
              {open && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden"
                >
                  <div className="border-t border-line/10 px-5 py-4">
                    <p className="text-sm leading-relaxed text-dim">{entry.review_text}</p>
                    <div className="mt-4 grid gap-5 md:grid-cols-2">
                      <div>
                        <h4 className="mb-2 font-mono text-[10px] uppercase tracking-wider text-faint">
                          Top tokens at the time
                        </h4>
                        <TopTokens tokens={tokens} limit={5} />
                      </div>
                      <div>
                        <h4 className="mb-2 font-mono text-[10px] uppercase tracking-wider text-faint">
                          Details
                        </h4>
                        <dl className="space-y-1.5 text-sm">
                          <div className="flex justify-between gap-4">
                            <dt className="text-faint">Fake probability</dt>
                            <dd className="font-mono text-ink">
                              {(entry.fake_probability * 100).toFixed(0)}%
                            </dd>
                          </div>
                          <div className="flex justify-between gap-4">
                            <dt className="text-faint">Sentiment compound</dt>
                            <dd className="font-mono text-ink">{entry.compound.toFixed(2)}</dd>
                          </div>
                          <div className="flex justify-between gap-4">
                            <dt className="text-faint">Flags</dt>
                            <dd className="font-mono text-ink">
                              {flags.length > 0 ? `${flags.length} triggered` : "none"}
                            </dd>
                          </div>
                        </dl>
                        <button
                          type="button"
                          onClick={() => onDelete(entry.id)}
                          className="mt-4 inline-flex items-center gap-2 rounded-pill border border-fake/30 px-3.5 py-1.5 text-xs text-fake transition-colors hover:bg-fake/10 active:scale-[0.97]"
                        >
                          <Trash2 className="h-3.5 w-3.5" aria-hidden /> Delete entry
                        </button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.li>
        );
      })}
    </ul>
  );
}
