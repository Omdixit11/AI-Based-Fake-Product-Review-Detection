"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { api, USE_MOCK } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";

type State = "loading" | "ok" | "down";

export function StatusChip() {
  const [state, setState] = useState<State>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    let cancelled = false;
    const ping = async () => {
      try {
        const h = await api.getHealth();
        if (!cancelled) {
          setHealth(h);
          setState("ok");
        }
      } catch {
        if (!cancelled) setState("down");
      }
    };
    ping();
    const t = window.setInterval(ping, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [pathname]);

  const dot =
    state === "ok"
      ? "bg-genuine shadow-[0_0_8px_rgb(var(--genuine))]"
      : state === "down"
        ? "bg-fake shadow-[0_0_8px_rgb(var(--fake))]"
        : "bg-warn animate-pulse-soft";

  const label = USE_MOCK
    ? "Mock data"
    : state === "ok"
      ? "API online"
      : state === "down"
        ? "API offline"
        : "Checking…";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-pill border border-line/15 bg-line/5 px-3 py-1.5",
        "font-mono text-[11px] text-dim"
      )}
      title={
        health
          ? `status=${health.status} · models_loaded=${health.models_loaded} · v${health.version}`
          : undefined
      }
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} aria-hidden />
      {label}
    </span>
  );
}
