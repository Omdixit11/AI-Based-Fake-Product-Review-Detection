"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  FileUp,
  FlaskConical,
  History,
  Home,
  Moon,
  ScanSearch,
  Sparkles,
  Sun,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/app/providers";
import { NAV_LINKS } from "@/lib/nav";
import { SAMPLE_REVIEWS } from "@/lib/utils";

/** Tiny event bus so the palette can ask the Analyze page to load a sample. */
export function requestSampleReview(review: string, rating?: number) {
  window.dispatchEvent(
    new CustomEvent("truthlens:load-sample", { detail: { review, rating } })
  );
}

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: React.ReactNode;
  run: () => void;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const router = useRouter();
  const { theme, toggle } = useTheme();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setIndex(0);
      window.setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    const nav: Command[] = [
      { id: "home", label: "Go to Landing", icon: <Home className="h-4 w-4" />, run: () => router.push("/") },
      ...NAV_LINKS.map((l) => ({
        id: `nav-${l.href}`,
        label: `Go to ${l.label}`,
        icon: <ArrowRight className="h-4 w-4" />,
        run: () => router.push(l.href),
      })),
    ];
    const actions: Command[] = [
      {
        id: "theme",
        label: theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
        icon: theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />,
        run: toggle,
      },
      ...SAMPLE_REVIEWS.map((s, i) => ({
        id: `sample-${i}`,
        label: `Load sample: ${s.label}`,
        hint: "Analyze",
        icon: <Sparkles className="h-4 w-4" />,
        run: () => {
          router.push("/analyze");
          window.setTimeout(() => requestSampleReview(s.review, s.rating), 350);
        },
      })),
    ];
    const all = [...nav, ...actions];
    const q = query.trim().toLowerCase();
    return q ? all.filter((c) => c.label.toLowerCase().includes(q)) : all;
  }, [query, router, theme, toggle]);

  useEffect(() => setIndex(0), [commands.length]);

  const runCommand = useCallback(
    (cmd: Command) => {
      setOpen(false);
      cmd.run();
    },
    []
  );

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setIndex((i) => Math.min(i + 1, commands.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && commands[index]) {
      e.preventDefault();
      runCommand(commands[index]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const sectionIcon = (id: string) =>
    id.startsWith("nav-/batch") ? <FileUp className="h-4 w-4" /> :
    id.startsWith("nav-/model-lab") ? <FlaskConical className="h-4 w-4" /> :
    id.startsWith("nav-/history") ? <History className="h-4 w-4" /> :
    id.startsWith("nav-/how") ? <Workflow className="h-4 w-4" /> :
    id.startsWith("nav-/analyze") ? <ScanSearch className="h-4 w-4" /> : null;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.14 }}
          className="fixed inset-0 z-[85] flex items-start justify-center bg-black/55 p-4 pt-[14vh] backdrop-blur-sm"
          onClick={() => setOpen(false)}
          role="presentation"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -8 }}
            transition={{ duration: 0.16 }}
            className="glass w-full max-w-lg overflow-hidden p-0"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
          >
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Type a command or search…"
              aria-label="Command search"
              className="w-full border-b border-line/10 bg-transparent px-5 py-4 font-display text-base text-ink placeholder:text-faint focus:outline-none"
            />
            <ul className="max-h-[46vh] overflow-y-auto p-2" role="listbox">
              {commands.length === 0 && (
                <li className="px-3 py-6 text-center text-sm text-faint">
                  No commands match “{query}”.
                </li>
              )}
              {commands.map((cmd, i) => (
                <li key={cmd.id}>
                  <button
                    role="option"
                    aria-selected={i === index}
                    onMouseEnter={() => setIndex(i)}
                    onClick={() => runCommand(cmd)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm",
                      i === index ? "bg-line/10 text-ink" : "text-dim"
                    )}
                  >
                    <span className="text-faint">{sectionIcon(cmd.id) ?? cmd.icon}</span>
                    <span className="flex-1">{cmd.label}</span>
                    {cmd.hint && (
                      <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
                        {cmd.hint}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex items-center gap-4 border-t border-line/10 px-5 py-2.5 font-mono text-[10px] text-faint">
              <span>↑↓ navigate</span>
              <span>↵ select</span>
              <span>esc close</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
