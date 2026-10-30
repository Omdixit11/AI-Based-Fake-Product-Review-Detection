"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

export function StarRating({
  value,
  onChange,
}: {
  value: number | undefined;
  onChange: (v: number | undefined) => void;
}) {
  const [hover, setHover] = useState(0);
  const shown = hover || value || 0;
  return (
    <div className="flex items-center gap-1" role="radiogroup" aria-label="Star rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} star${n === 1 ? "" : "s"}`}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onChange(value === n ? undefined : n)}
          className="rounded p-0.5 transition-transform hover:scale-110 active:scale-95"
        >
          <Star
            className={cn(
              "h-5 w-5 transition-colors",
              n <= shown ? "fill-warn text-warn" : "text-faint"
            )}
            aria-hidden
          />
        </button>
      ))}
      {value !== undefined && (
        <button
          type="button"
          onClick={() => onChange(undefined)}
          className="ml-1 text-[11px] text-faint underline-offset-2 hover:text-dim hover:underline"
        >
          clear
        </button>
      )}
    </div>
  );
}
