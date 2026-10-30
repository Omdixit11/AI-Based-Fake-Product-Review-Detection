"use client";

import { useEffect, useMemo, useState } from "react";
import { Database, FlaskConical, Layers } from "lucide-react";
import { api } from "@/lib/api";
import type { FeatureSet, MetricsResponse } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { Chip, Skeleton } from "@/components/ui/chip";
import { MetricCards } from "@/components/lab/MetricCards";
import { ComparisonBars } from "@/components/lab/ComparisonBars";
import { ConfusionMatrix } from "@/components/lab/ConfusionMatrix";
import { RocChart } from "@/components/lab/RocChart";
import { formatNumber } from "@/lib/utils";

const FEATURE_SETS: Array<{ value: FeatureSet; label: string }> = [
  { value: "tfidf_only", label: "TF-IDF only" },
  { value: "tfidf_sentiment", label: "TF-IDF + sentiment" },
];

export default function ModelLabPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [featureSet, setFeatureSet] = useState<FeatureSet>("tfidf_sentiment");

  useEffect(() => {
    let cancelled = false;
    api
      .getMetrics()
      .then((m) => {
        if (!cancelled) {
          setMetrics(m);
          setFeatureSet(m.active_feature_set);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load metrics.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const nb = metrics?.models.nb[featureSet];
  const svm = metrics?.models.svm[featureSet];

  const rocSeries = useMemo(() => {
    if (!nb || !svm) return [];
    return [
      { name: "Naive Bayes", curve: nb.roc_curve, color: "rgb(var(--brand))", auc: nb.roc_auc },
      { name: "SVM", curve: svm.roc_curve, color: "rgb(var(--aqua))", auc: svm.roc_auc },
    ];
  }, [nb, svm]);

  if (error) {
    return (
      <div className="mx-auto w-full max-w-shell px-4 pb-16">
        <Card className="border-fake/30">
          <h1 className="font-display text-lg font-semibold text-fake">Model Lab unavailable</h1>
          <p className="mt-1 text-sm text-dim">{error}</p>
        </Card>
      </div>
    );
  }

  if (!metrics || !nb || !svm) {
    return (
      <div className="mx-auto w-full max-w-shell px-4 pb-16">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="mt-6 h-28" />
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-44" />
          <Skeleton className="h-44" />
        </div>
        <Skeleton className="mt-6 h-72" />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-shell px-4 pb-16">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
          Model Lab
        </h1>
        <p className="mt-2 max-w-xl text-sm text-dim">
          How the models were trained and how they scored — every number here comes
          straight from the training pipeline.
        </p>
      </div>

      {/* Dataset info + feature-set toggle */}
      <div className="mb-6 grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader
            title="Dataset"
            subtitle={metrics.dataset.name}
            action={<Database className="h-4 w-4 text-faint" aria-hidden />}
          />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {(
              [
                ["Reviews", formatNumber(metrics.dataset.size)],
                ["Train", formatNumber(metrics.dataset.train_size)],
                ["Test", formatNumber(metrics.dataset.test_size)],
                ["Fake share", `${metrics.dataset.fake_percent.toFixed(0)}%`],
                ["Avg words", metrics.dataset.avg_words.toFixed(1)],
              ] as const
            ).map(([label, value]) => (
              <div key={label}>
                <div className="font-mono text-xl font-bold text-ink">{value}</div>
                <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-faint">
                  {label}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Feature set"
            subtitle="Toggle to compare the two feature regimes"
            action={<Layers className="h-4 w-4 text-faint" aria-hidden />}
          />
          <div className="flex flex-col gap-2">
            {FEATURE_SETS.map((f) => (
              <Chip
                key={f.value}
                active={featureSet === f.value}
                onClick={() => setFeatureSet(f.value)}
                className="justify-center py-2 text-sm"
              >
                {f.label}
                {metrics.active_feature_set === f.value && (
                  <span className="font-mono text-[10px] text-faint">· pipeline default</span>
                )}
              </Chip>
            ))}
          </div>
        </Card>
      </div>

      {/* Per-model metric cards */}
      <div className="mb-6 grid gap-4 xl:grid-cols-2">
        {(
          [
            { name: "Naive Bayes", m: nb, isBest: metrics.best_model === "nb", accent: "brand" as const },
            { name: "SVM", m: svm, isBest: metrics.best_model === "svm", accent: "aqua" as const },
          ] as const
        ).map((mo) => (
          <Card key={mo.name}>
            <CardHeader
              title={mo.name}
              subtitle={`ROC-AUC ${mo.m.roc_auc.toFixed(3)} · ${mo.isBest ? "selected as the best model" : "runner-up on this dataset"}`}
              action={
                mo.isBest ? (
                  <span className="rounded-pill bg-genuine/12 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-genuine ring-1 ring-genuine/25">
                    Best
                  </span>
                ) : (
                  <FlaskConical className="h-4 w-4 text-faint" aria-hidden />
                )
              }
            />
            <MetricCards metrics={mo.m} isBest={mo.isBest} accent={mo.accent} />
          </Card>
        ))}
      </div>

      {/* Comparison + ROC */}
      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Head-to-head" subtitle="Naive Bayes vs SVM" />
          <ComparisonBars nb={nb} svm={svm} />
        </Card>
        <Card>
          <CardHeader title="ROC curves" subtitle="True positive rate vs false positive rate" />
          <RocChart series={rocSeries} />
        </Card>
      </div>

      {/* Confusion matrices */}
      <Card>
        <CardHeader
          title="Confusion matrices"
          subtitle="Positive class = fake · [[TN, FP], [FN, TP]]"
        />
        <div className="grid gap-8 sm:grid-cols-2">
          <ConfusionMatrix matrix={nb.confusion_matrix} title="Naive Bayes" />
          <ConfusionMatrix matrix={svm.confusion_matrix} title="SVM" />
        </div>
      </Card>
    </div>
  );
}
