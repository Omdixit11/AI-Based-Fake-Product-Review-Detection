import { cn } from "@/lib/utils";

/** TruthLens mark: a lens/eye with a scan line. */
export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden className={cn("h-7 w-7", className)}>
      <defs>
        <linearGradient id="tl-g" x1="4" y1="4" x2="28" y2="28">
          <stop offset="0" stopColor="rgb(var(--brand))" />
          <stop offset="1" stopColor="rgb(var(--aqua))" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="28" height="28" rx="9" stroke="url(#tl-g)" strokeWidth="2" />
      <circle cx="16" cy="16" r="6.5" stroke="url(#tl-g)" strokeWidth="2" />
      <circle cx="16" cy="16" r="2.2" fill="url(#tl-g)" />
      <line x1="7" y1="16" x2="11" y2="16" stroke="url(#tl-g)" strokeWidth="2" strokeLinecap="round" />
      <line x1="21" y1="16" x2="25" y2="16" stroke="url(#tl-g)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <Logo />
      <span className="font-display text-lg font-bold tracking-tight text-ink">
        Truth<span className="text-gradient">Lens</span>
      </span>
    </span>
  );
}
