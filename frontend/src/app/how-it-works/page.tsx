"use client";

import { motion } from "framer-motion";
import { BookOpenText, Percent, Sigma, Waves } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/card";
import { PipelineVisual } from "@/components/how-it-works/PipelineVisual";

const CONCEPTS = [
  {
    icon: Percent,
    title: "TF-IDF",
    tagline: "Which words matter",
    body: "TF-IDF counts how often a word appears in a review, discounted by how common it is everywhere. “Amazing” in one review is signal; “the” is not. The result is a numeric fingerprint of the review’s vocabulary.",
  },
  {
    icon: Sigma,
    title: "Naive Bayes",
    tagline: "Multiply the evidence",
    body: "A probabilistic classic: it assumes words are independent and multiplies how strongly each word suggests fake or genuine. Fast, robust, and surprisingly hard to beat on short text.",
  },
  {
    icon: Waves,
    title: "VADER sentiment",
    tagline: "How emotional is it",
    body: "A lexicon-based sentiment scorer tuned for social text. Fake reviews often ride emotional extremes, so VADER’s compound score — and its distance from the review’s star rating — becomes a useful feature.",
  },
  {
    icon: BookOpenText,
    title: "SVM",
    tagline: "Draw the boundary",
    body: "A Support Vector Machine finds the hyperplane that best separates fake from genuine reviews in feature space, with the widest margin. Calibration turns its distance into a probability you can trust.",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto w-full max-w-shell px-4 pb-16">
      <div className="mb-10">
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
          How TruthLens works
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-dim">
          No black box. A review travels through seven transparent stages, and every
          verdict ships with the evidence that produced it.
        </p>
      </div>

      <Card className="mb-10">
        <CardHeader title="The pipeline" subtitle="From raw text to verdict, step by step" />
        <PipelineVisual />
      </Card>

      <h2 className="mb-4 font-display text-xl font-bold tracking-tight text-ink">
        The concepts, in plain language
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {CONCEPTS.map((c, i) => {
          const Icon = c.icon;
          return (
            <motion.div
              key={c.title}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.06, duration: 0.35 }}
            >
              <Card className="h-full">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand/15 to-aqua/15 text-aqua">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <div>
                    <h3 className="font-display text-base font-semibold text-ink">{c.title}</h3>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-faint">
                      {c.tagline}
                    </p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-dim">{c.body}</p>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
