"use client";

import { useMemo, useState } from "react";
import type { TokenScore } from "@/lib/types";
import { Tooltip } from "@/components/ui/tooltip";

/**
 * Renders the analyzed review with each word tinted by the contribution
 * score of its token: coral = fake-leaning, mint = genuine-leaning.
 * Hover a word to see its exact score. User text is rendered as plain
 * React text nodes — never as HTML.
 */
export function HighlightedText({
  text,
  tokens,
}: {
  text: string;
  tokens: TokenScore[];
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  const scoreMap = useMemo(() => {
    const m = new Map<string, TokenScore>();
    for (const t of tokens) m.set(t.token.toLowerCase(), t);
    return m;
  }, [tokens]);

  const maxAbs = useMemo(
    () => Math.max(0.2, ...tokens.map((t) => Math.abs(t.score))),
    [tokens]
  );

  const parts = useMemo(() => {
    // Split into words while keeping separators, so we can style words only.
    return text.split(/(\s+)/).map((part, i) => ({ part, i }));
  }, [text]);

  return (
    <p className="text-sm leading-7 text-dim">
      {parts.map(({ part, i }) => {
        const key = part.toLowerCase().replace(/[^a-z']/g, "");
        const score = key ? scoreMap.get(key) : undefined;
        if (!score) return <span key={i}>{part}</span>;

        const intensity = Math.min(Math.abs(score.score) / maxAbs, 1);
        const fake = score.direction === "fake";
        const bg = fake
          ? `rgb(var(--fake) / ${0.08 + intensity * 0.28})`
          : `rgb(var(--genuine) / ${0.08 + intensity * 0.24})`;
        const color = fake
          ? `color-mix(in srgb, rgb(var(--fake)) ${45 + intensity * 55}%, rgb(var(--ink)))`
          : `color-mix(in srgb, rgb(var(--genuine)) ${45 + intensity * 55}%, rgb(var(--ink)))`;

        const chip = (
          <span
            key={i}
            onMouseEnter={() => setHovered(score.token)}
            onMouseLeave={() => setHovered(null)}
            className="cursor-help rounded px-0.5 transition-transform"
            style={{ background: bg, color, boxShadow: hovered === score.token ? `0 1px 0 ${fake ? "rgb(var(--fake))" : "rgb(var(--genuine))"}` : undefined }}
          >
            {part}
          </span>
        );

        return (
          <Tooltip
            key={i}
            content={
              <span>
                {score.token} · {score.score > 0 ? "+" : ""}
                {score.score.toFixed(2)} → {score.direction}
              </span>
            }
          >
            {chip}
          </Tooltip>
        );
      })}
    </p>
  );
}
