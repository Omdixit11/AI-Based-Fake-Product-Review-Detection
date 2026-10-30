"use client";

import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Chip } from "@/components/ui/chip";

export function HistoryFilters({
  search,
  onSearchChange,
  verdict,
  onVerdictChange,
  onClearAll,
}: {
  search: string;
  onSearchChange: (v: string) => void;
  verdict: "all" | "fake" | "genuine";
  onVerdictChange: (v: "all" | "fake" | "genuine") => void;
  onClearAll: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
        <Search
          className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-faint"
          aria-hidden
        />
        <input
          type="search"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search reviews…"
          aria-label="Search history"
          className={cn(
            "h-10 w-full rounded-pill border border-line/15 bg-line/5 pl-10 pr-9 text-sm text-ink",
            "placeholder:text-faint focus:border-aqua/40 focus:outline-none"
          )}
        />
        {search && (
          <button
            type="button"
            onClick={() => onSearchChange("")}
            aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="flex gap-2" role="radiogroup" aria-label="Verdict filter">
        {(["all", "fake", "genuine"] as const).map((v) => (
          <Chip key={v} active={verdict === v} onClick={() => onVerdictChange(v)}>
            {v === "all" ? "All" : v === "fake" ? "Fake" : "Genuine"}
          </Chip>
        ))}
      </div>

      <button
        type="button"
        onClick={onClearAll}
        className="ml-auto rounded-pill border border-fake/30 px-4 py-2 text-sm text-fake transition-colors hover:bg-fake/10 active:scale-[0.97]"
      >
        Clear all…
      </button>
    </div>
  );
}
