import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { PredictMetadata } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Phase 3.5 — normalise the optional predict metadata before it is sent.
 * The backend uses extra="forbid" and rejects a blank user_id, so only fields
 * the reviewer actually filled in survive; an empty object becomes undefined,
 * which makes the request identical to a Phase 3 one.
 */
export function cleanMetadata(
  metadata: PredictMetadata | undefined
): PredictMetadata | undefined {
  if (!metadata) return undefined;
  const out: PredictMetadata = {};
  const userId = metadata.user_id?.trim();
  if (userId) out.user_id = userId.slice(0, 128);
  if (metadata.posted_at) out.posted_at = metadata.posted_at;
  const velocity = metadata.reviews_last_minute;
  if (typeof velocity === "number" && Number.isFinite(velocity)) {
    out.reviews_last_minute = Math.max(0, Math.min(10000, Math.round(velocity)));
  }
  return Object.keys(out).length ? out : undefined;
}

/** True when a prediction came from the Tier-1 rules instead of a model. */
export function isRuleDecision(modelUsed: string): boolean {
  return modelUsed === "tier1_rules";
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatPercentFromWhole(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/** "2026-10-30T09:12:00Z" -> "12 minutes ago" */
export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 45) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} mo ago`;
  return `${Math.floor(months / 12)} y ago`;
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}

/** Escape a cell for CSV export. */
export function csvCell(value: string | number): string {
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function downloadTextFile(filename: string, content: string, mime = "text/csv") {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Parse the CSV template the Batch page offers for download. */
export const BATCH_TEMPLATE_CSV = `review,rating
"This product is absolutely AMAZING!!! Best thing ever, buy it now!!!",5
"Does what it says on the box. Setup was quick and it has worked fine for a month.",4
"Broke after two days and support never replied. Avoid.",1
"Decent quality for the price, though shipping was slow.",3
"I LOVE this so much!! Perfect gift, my whole family wants one now!!",5
`;

export const SAMPLE_REVIEWS = [
  {
    label: "Over-hyped spam",
    review:
      "OMG this is the BEST product I have EVER bought!!! Absolutely AMAZING quality, my life is CHANGED forever!!! Buy it NOW, you will NOT regret it!!! Five stars!!!!",
    rating: 5,
  },
  {
    label: "Balanced genuine",
    review:
      "I've been using it for about a month now. Build quality is good and it does what the description says. The app pairing was a bit finicky at first but fine after an update. Would recommend at this price.",
    rating: 4,
  },
  {
    label: "Honest complaint",
    review:
      "Stopped working after two weeks. I contacted support twice and never got a reply. The battery also drains much faster than advertised. Disappointed.",
    rating: 1,
  },
] as const;
