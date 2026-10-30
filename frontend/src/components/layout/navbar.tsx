"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, ScanSearch, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { pressable } from "@/app/providers";
import { Wordmark } from "./logo";
import { StatusChip } from "./status-chip";
import { ThemeToggle } from "./theme-toggle";
import { NAV_LINKS } from "@/lib/nav";

export function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="fixed inset-x-0 top-4 z-50 flex justify-center px-4">
      <nav
        aria-label="Primary"
        className="glass flex w-full max-w-shell items-center gap-2 px-3 py-2"
      >
        <Link
          href="/"
          className="mr-1 rounded-lg px-1.5 py-1"
          aria-label="TruthLens home"
        >
          <Wordmark />
        </Link>

        {/* Desktop links with animated active pill */}
        <div className="mx-auto hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  pressable,
                  "relative rounded-pill px-3.5 py-2 text-sm transition-colors",
                  active ? "text-ink" : "text-dim hover:text-ink"
                )}
              >
                {active && (
                  <motion.span
                    layoutId="nav-active-pill"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    className="absolute inset-0 rounded-pill bg-line/10 ring-1 ring-line/15"
                  />
                )}
                <span className="relative z-10">{link.label}</span>
              </Link>
            );
          })}
        </div>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          <StatusChip />
          <ThemeToggle />
          <Link
            href="/analyze"
            className={cn(
              pressable,
              "inline-flex h-9 items-center gap-2 rounded-pill bg-gradient-to-r from-brand to-aqua px-4 text-sm font-semibold text-white shadow-glow-brand hover:brightness-110"
            )}
          >
            <ScanSearch className="h-4 w-4" aria-hidden />
            Scan a review
          </Link>
        </div>

        {/* Mobile controls */}
        <div className="ml-auto flex items-center gap-2 md:hidden">
          <StatusChip />
          <ThemeToggle />
          <button
            className={cn(pressable, "flex h-8 w-8 items-center justify-center rounded-pill border border-line/15 text-dim")}
            onClick={() => setMobileOpen((o) => !o)}
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            className="glass absolute top-[calc(100%+8px)] w-[calc(100%-2rem)] max-w-shell p-2 md:hidden"
          >
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "block rounded-xl px-4 py-3 text-sm",
                  pathname.startsWith(link.href)
                    ? "bg-line/10 font-medium text-ink"
                    : "text-dim hover:bg-line/5 hover:text-ink"
                )}
              >
                {link.label}
              </Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
