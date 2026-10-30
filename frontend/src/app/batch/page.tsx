"use client";

import { useCallback, useState } from "react";
import { FileDown, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import type { BatchResult } from "@/lib/types";
import { useToast } from "@/app/providers";
import { Button } from "@/components/ui/button";
import { DropZone } from "@/components/batch/DropZone";
import { SummaryStats } from "@/components/batch/SummaryStats";
import { ResultsTable } from "@/components/batch/ResultsTable";
import { csvCell, downloadTextFile } from "@/lib/utils";

export default function BatchPage() {
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState<string | undefined>();
  const [result, setResult] = useState<BatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const onFile = useCallback(
    async (text: string, name: string) => {
      setBusy(true);
      setFileName(name);
      setError(null);
      setResult(null);
      try {
        const res = await api.predictBatch(text, name);
        setResult(res);
        toast(
          res.summary.fake_percent >= 50 ? "info" : "success",
          `Analyzed ${res.summary.total} reviews — ${res.summary.fake_count} flagged as fake.`
        );
      } catch (e) {
        const message = e instanceof Error ? e.message : "Batch analysis failed.";
        setError(message);
        toast("error", message);
      } finally {
        setBusy(false);
      }
    },
    [toast]
  );

  const exportCsv = useCallback(() => {
    if (!result) return;
    const header = ["row", "review", "rating", "verdict", "fake_probability", "confidence", "sentiment"];
    const lines = [
      header.join(","),
      ...result.rows.map((r) =>
        [
          r.row,
          csvCell(r.review),
          r.rating ?? "",
          r.verdict,
          r.fake_probability,
          r.confidence,
          csvCell(r.sentiment_label),
        ].join(",")
      ),
    ];
    downloadTextFile("truthlens-batch-results.csv", lines.join("\n"));
    toast("success", "Results exported as CSV.");
  }, [result, toast]);

  const reset = useCallback(() => {
    setResult(null);
    setFileName(undefined);
    setError(null);
  }, []);

  return (
    <div className="mx-auto w-full max-w-shell px-4 pb-16">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
            Batch analysis
          </h1>
          <p className="mt-2 max-w-xl text-sm text-dim">
            Upload a CSV of reviews (column <span className="font-mono text-ink">review</span>,
            optional <span className="font-mono text-ink">rating</span>) and get a full forensic
            sweep with a summary you can export.
          </p>
        </div>
        {result && (
          <div className="flex gap-3">
            <Button variant="secondary" onClick={reset}>
              <RotateCcw className="h-4 w-4" aria-hidden /> New batch
            </Button>
            <Button onClick={exportCsv}>
              <FileDown className="h-4 w-4" aria-hidden /> Export CSV
            </Button>
          </div>
        )}
      </div>

      <div aria-live="polite" className="flex flex-col gap-6">
        {!result && <DropZone onFile={onFile} busy={busy} fileName={fileName} />}
        {error && !busy && (
          <div className="glass border-fake/30 p-6">
            <h2 className="font-display text-lg font-semibold text-fake">Batch failed</h2>
            <p className="mt-1 text-sm text-dim">{error}</p>
          </div>
        )}
        {result && <SummaryStats summary={result.summary} />}
        {result && <ResultsTable rows={result.rows} />}
      </div>
    </div>
  );
}
