import Link from "next/link";
import { Wordmark } from "./logo";
import { NAV_LINKS } from "@/lib/nav";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line/10">
      <div className="mx-auto flex w-full max-w-shell flex-col gap-8 px-4 py-12 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm">
          <Wordmark />
          <p className="mt-3 text-sm leading-relaxed text-faint">
            Forensic-grade review analysis. TF-IDF, VADER sentiment and
            classical machine learning, explained in plain sight.
          </p>
        </div>
        <nav aria-label="Footer" className="grid grid-cols-2 gap-x-12 gap-y-2">
          {NAV_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-sm text-dim transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="border-t border-line/10">
        <div className="mx-auto flex w-full max-w-shell flex-wrap items-center justify-between gap-2 px-4 py-4 font-mono text-[11px] text-faint">
          <span>TruthLens · v0.1.0</span>
          <span>Classical ML — NB + SVM · TF-IDF + VADER</span>
        </div>
      </div>
    </footer>
  );
}
