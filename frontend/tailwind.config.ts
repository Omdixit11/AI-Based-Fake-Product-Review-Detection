import type { Config } from "tailwindcss";

/**
 * Design tokens for the "Forensic Intelligence" design language.
 * Raw RGB triplets live in styles/globals.css as CSS variables;
 * here we only map Tailwind names onto those variables.
 */
const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        elevate: "rgb(var(--bg-elevate) / <alpha-value>)",
        card: "rgb(var(--card) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        dim: "rgb(var(--ink-dim) / <alpha-value>)",
        faint: "rgb(var(--ink-faint) / <alpha-value>)",
        brand: "rgb(var(--brand) / <alpha-value>)",
        aqua: "rgb(var(--aqua) / <alpha-value>)",
        fake: "rgb(var(--fake) / <alpha-value>)",
        genuine: "rgb(var(--genuine) / <alpha-value>)",
        warn: "rgb(var(--warn) / <alpha-value>)",
      },
      fontFamily: {
        display: ["var(--font-grotesk)", "system-ui", "sans-serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "var(--radius-card)",
        pill: "var(--radius-pill)",
      },
      boxShadow: {
        glass: "var(--shadow-glass)",
        lift: "var(--shadow-lift)",
        "glow-fake": "0 0 48px -10px rgb(var(--fake) / 0.55)",
        "glow-genuine": "0 0 48px -10px rgb(var(--genuine) / 0.5)",
        "glow-brand": "0 0 56px -12px rgb(var(--brand) / 0.6)",
      },
      maxWidth: {
        shell: "1240px",
      },
      keyframes: {
        "aurora-drift": {
          "0%, 100%": { transform: "translate3d(-6%, -4%, 0) scale(1)" },
          "50%": { transform: "translate3d(7%, 6%, 0) scale(1.15)" },
        },
        "aurora-drift-2": {
          "0%, 100%": { transform: "translate3d(5%, 8%, 0) scale(1.1)" },
          "50%": { transform: "translate3d(-8%, -5%, 0) scale(0.95)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-600px 0" },
          "100%": { backgroundPosition: "600px 0" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
        "scan-sweep": {
          "0%": { top: "-10%" },
          "100%": { top: "110%" },
        },
        "flow-dash": {
          to: { strokeDashoffset: "-24" },
        },
      },
      animation: {
        "aurora-drift": "aurora-drift 26s ease-in-out infinite",
        "aurora-drift-2": "aurora-drift-2 32s ease-in-out infinite",
        shimmer: "shimmer 1.8s linear infinite",
        "pulse-soft": "pulse-soft 2.4s ease-in-out infinite",
        "scan-sweep": "scan-sweep 1.6s ease-in-out infinite",
        "flow-dash": "flow-dash 1.2s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
