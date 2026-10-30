"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { HistoryEntry, HistoryListResponse } from "@/lib/types";
import { useToast } from "@/app/providers";
import { HistoryFilters } from "@/components/history/HistoryFilters";
import { HistoryList } from "@/components/history/HistoryList";
import { Skeleton } from "@/components/ui/chip";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export default function HistoryPage() {
  const [data, setData] = useState<HistoryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [verdict, setVerdict] = useState<"all" | "fake" | "genuine">("all");
  const [confirmClear, setConfirmClear] = useState(false);
  const { toast } = useToast();
  const debounceRef = useRef<number>(0);

  const load = useCallback(async (searchValue: string, verdictValue: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getHistory({ search: searchValue, verdict: verdictValue, limit: 100 });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced reload when search/verdict change.
  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    const t = window.setTimeout(() => load(search, verdict), 250);
    return () => window.clearTimeout(t);
  }, [search, verdict, load]);

  const deleteEntry = useCallback(
    async (id: number) => {
      try {
        await api.deleteHistoryEntry(id);
        setData((d) =>
          d ? { total: Math.max(0, d.total - 1), entries: d.entries.filter((e) => e.id !== id) } : d
        );
        toast("success", "Entry deleted.");
      } catch (e) {
        toast("error", e instanceof Error ? e.message : "Delete failed.");
      }
    },
    [toast]
  );

  const clearAll = useCallback(async () => {
    setConfirmClear(false);
    try {
      await api.clearHistory();
      setData({ total: 0, entries: [] as HistoryEntry[] });
      toast("success", "History cleared.");
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Clear failed.");
    }
  }, [toast]);

  return (
    <div className="mx-auto w-full max-w-shell px-4 pb-16">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
          History
        </h1>
        <p className="mt-2 max-w-xl text-sm text-dim">
          Every scan is recorded — search, filter, expand and delete past analyses.
        </p>
      </div>

      <div className="mb-6">
        <HistoryFilters
          search={search}
          onSearchChange={setSearch}
          verdict={verdict}
          onVerdictChange={setVerdict}
          onClearAll={() => setConfirmClear(true)}
        />
      </div>

      <div aria-live="polite">
        {loading && !data && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        )}
        {error && (
          <div className="glass border-fake/30 p-6">
            <h2 className="font-display text-lg font-semibold text-fake">History unavailable</h2>
            <p className="mt-1 text-sm text-dim">{error}</p>
          </div>
        )}
        {data && !loading && (
          <>
            <p className="mb-3 font-mono text-[11px] text-faint">
              {data.total} entr{data.total === 1 ? "y" : "ies"}
              {search && ` matching “${search}”`}
            </p>
            <HistoryList entries={data.entries} onDelete={deleteEntry} />
          </>
        )}
        {data && loading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        )}
      </div>

      <Modal
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Clear all history?"
        danger
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmClear(false)}>
              Keep entries
            </Button>
            <Button variant="danger" onClick={clearAll}>
              Clear everything
            </Button>
          </>
        }
      >
        This permanently deletes all recorded analyses, including the tokens and flags
        captured for each one. There is no undo.
      </Modal>
    </div>
  );
}
