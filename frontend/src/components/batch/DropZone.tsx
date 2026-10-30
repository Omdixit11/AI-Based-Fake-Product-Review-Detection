"use client";

import { useCallback, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FileDown, FileUp, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { BATCH_TEMPLATE_CSV, downloadTextFile } from "@/lib/utils";

/**
 * CSV drag-and-drop zone with template download and read progress.
 * The actual analysis happens in the page; this component only reads
 * the file into text.
 */
export function DropZone({
  onFile,
  busy,
  fileName,
  progress,
}: {
  onFile: (text: string, name: string) => void;
  busy: boolean;
  fileName?: string;
  progress?: number; // 0..1
}) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const readFile = useCallback(
    (file: File) => {
      if (!file.name.toLowerCase().endsWith(".csv") && file.type !== "text/csv") {
        setError("Only CSV files are accepted.");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setError("File is larger than the 5 MB limit.");
        return;
      }
      setError(null);
      const reader = new FileReader();
      reader.onprogress = (e) => {
        if (e.lengthComputable && onProgressRef.current) {
          onProgressRef.current(e.loaded / e.total);
        }
      };
      reader.onload = () => {
        onProgressRef.current?.(1);
        onFile(String(reader.result ?? ""), file.name);
      };
      reader.onerror = () => setError("Could not read the file.");
      reader.readAsText(file);
    },
    [onFile]
  );

  const onProgressRef = useRef<((p: number) => void) | null>(null);
  const [progressState, setProgressState] = useState(0);
  onProgressRef.current = (p: number) => setProgressState(p);

  const effectiveProgress = progress ?? progressState;

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a CSV of reviews"
        onClick={() => !busy && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !busy) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!busy && e.dataTransfer.files[0]) readFile(e.dataTransfer.files[0]);
        }}
        className={cn(
          "relative flex min-h-[220px] cursor-pointer flex-col items-center justify-center gap-4 overflow-hidden rounded-card border-2 border-dashed p-8 text-center transition-colors",
          dragging
            ? "border-aqua/60 bg-aqua/6"
            : "border-line/20 bg-line/4 hover:border-line/35 hover:bg-line/6",
          busy && "pointer-events-none opacity-70"
        )}
      >
        <AnimatePresence>
          {busy && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-x-0 bottom-0 h-1 bg-line/10"
            >
              <motion.div
                className="h-full bg-gradient-to-r from-brand to-aqua"
                animate={{ width: `${Math.round(effectiveProgress * 100)}%` }}
                transition={{ duration: 0.2 }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <motion.span
          animate={dragging ? { scale: 1.12, y: -4 } : { scale: 1, y: 0 }}
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-2xl",
            dragging ? "bg-aqua/15 text-aqua" : "bg-line/8 text-faint"
          )}
        >
          {busy ? <Loader2 className="h-6 w-6 animate-spin" /> : <FileUp className="h-6 w-6" />}
        </motion.span>

        <div>
          <p className="font-display text-base font-semibold text-ink">
            {busy ? "Analyzing batch…" : "Drop your reviews CSV here"}
          </p>
          <p className="mt-1 text-sm text-faint">
            {fileName && busy ? fileName : "or click to browse — max 5000 rows, 5 MB"}
          </p>
          {error && <p className="mt-2 text-sm text-fake">{error}</p>}
        </div>

        {!busy && (
          <p className="font-mono text-[11px] text-faint">
            required column: <span className="text-ink">review</span> · optional:{" "}
            <span className="text-ink">rating</span>
          </p>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) readFile(f);
            e.target.value = "";
          }}
        />
      </div>

      <div className="mt-3 flex justify-center">
        <Button
          variant="secondary"
          size="sm"
          onClick={() =>
            downloadTextFile("truthlens-batch-template.csv", BATCH_TEMPLATE_CSV)
          }
        >
          <FileDown className="h-4 w-4" aria-hidden /> Download CSV template
        </Button>
      </div>
    </div>
  );
}
