"use client";

import { useEffect, useRef, useState } from "react";
import { animate, motion, useReducedMotion } from "framer-motion";

/**
 * Custom SVG radial gauge for the fake probability.
 * The stroke sweeps in on reveal and the number counts up;
 * color shifts mint -> amber -> coral as fake probability rises.
 */
export function ConfidenceGauge({
  fakeProbability,
  size = 220,
  label = "Fake probability",
}: {
  fakeProbability: number; // 0..1
  size?: number;
  label?: string;
}) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(0);
  const previous = useRef(0);

  const p = Math.max(0, Math.min(1, fakeProbability));
  const fraction = reduce ? p : display;

  useEffect(() => {
    if (reduce) {
      setDisplay(p);
      return;
    }
    const controls = animate(previous.current, p, {
      duration: 0.9,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setDisplay(v),
    });
    previous.current = p;
    return () => controls.stop();
  }, [p, reduce]);

  // Color ramp: mint (<0.35) -> amber (~0.6) -> coral (>0.8)
  const color =
    p < 0.35 ? "rgb(var(--genuine))" : p > 0.7 ? "rgb(var(--fake))" : "rgb(var(--warn))";

  const strokeWidth = 14;
  const r = (size - strokeWidth) / 2 - 6;
  const cx = size / 2;
  const circumference = 2 * Math.PI * r;
  // Gauge spans 240 degrees, opening at the bottom.
  const arcFraction = 240 / 360;
  const arcLength = circumference * arcFraction;
  const gap = circumference * (1 - arcFraction);

  const angle = -210; // start angle
  const valueLength = arcLength * fraction;

  const gradId = `gauge-grad-${size}`;

  return (
    <div className="flex flex-col items-center" role="img"
      aria-label={`${label}: ${Math.round(p * 100)} percent`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <defs>
          <linearGradient id={gradId} x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} />
            <stop offset="100%" stopColor={color} stopOpacity="0.65" />
          </linearGradient>
        </defs>
        {/* Track */}
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke="rgb(var(--line) / 0.12)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${gap}`}
          transform={`rotate(${angle} ${cx} ${cx})`}
        />
        {/* Value arc */}
        <motion.circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${Math.max(valueLength, 0.001)} ${circumference}`}
          transform={`rotate(${angle} ${cx} ${cx})`}
          style={{ filter: `drop-shadow(0 0 12px ${color})` }}
          initial={false}
        />
      </svg>
      <div className="-mt-[62%] flex flex-col items-center">
        <span
          className="font-mono text-5xl font-bold tracking-tight"
          style={{ color }}
        >
          {Math.round(fraction * 100)}
          <span className="text-2xl">%</span>
        </span>
        <span className="mt-1 max-w-[12rem] text-center text-xs text-faint">{label}</span>
      </div>
    </div>
  );
}
