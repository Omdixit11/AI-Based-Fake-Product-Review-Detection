"""Evaluation helpers and metrics.json writing."""
from __future__ import annotations

import json

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from .config import METRICS_PATH, MODELS_DIR, MAX_ARTIFACT_MB

MODEL_ORDER = ("nb", "svm")
FEATURE_ORDER = ("tfidf_only", "tfidf_sentiment")
MAX_CURVE_POINTS = 100


def _round(value) -> float:
    return round(float(value), 4)


def downsample_curve(fpr, tpr, max_points: int = MAX_CURVE_POINTS) -> dict:
    fpr = np.asarray(fpr, dtype=float)
    tpr = np.asarray(tpr, dtype=float)
    if len(fpr) > max_points:
        idx = np.unique(
            np.linspace(0, len(fpr) - 1, max_points).round().astype(int)
        )
        fpr, tpr = fpr[idx], tpr[idx]
    return {
        "fpr": [_round(v) for v in fpr],
        "tpr": [_round(v) for v in tpr],
    }


def evaluate_model(model, X_test, y_test) -> dict:
    """Compute the metrics block required by the metrics.json contract."""
    y_test = np.asarray(y_test)
    y_pred = model.predict(X_test)
    y_prob = np.asarray(model.predict_proba(X_test))[:, 1]

    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    fpr, tpr, _ = roc_curve(y_test, y_prob)

    return {
        "accuracy": _round(accuracy_score(y_test, y_pred)),
        "precision": _round(precision_score(y_test, y_pred, zero_division=0)),
        "recall": _round(recall_score(y_test, y_pred, zero_division=0)),
        "f1": _round(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": _round(roc_auc_score(y_test, y_prob)),
        "confusion_matrix": [[int(v) for v in row] for row in cm],
        "roc_curve": downsample_curve(fpr, tpr),
    }


def select_best(results: dict) -> tuple[str, str]:
    """Pick ``(model, feature_set)`` by F1, tie-broken by ROC-AUC."""
    keys = sorted(
        results,
        key=lambda k: (results[k]["f1"], results[k]["roc_auc"]),
        reverse=True,
    )
    return keys[0]


def write_metrics(metrics: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def print_summary(metrics: dict) -> None:
    header = (
        f"{'model':<5} {'features':<16} {'acc':>7} {'prec':>7} "
        f"{'rec':>7} {'f1':>7} {'auc':>7}  params"
    )
    print("\n" + header)
    print("-" * len(header))
    for model in MODEL_ORDER:
        for feature_set in FEATURE_ORDER:
            block = metrics["models"][model][feature_set]
            print(
                f"{model:<5} {feature_set:<16} "
                f"{block['accuracy']:>7.4f} {block['precision']:>7.4f} "
                f"{block['recall']:>7.4f} {block['f1']:>7.4f} "
                f"{block['roc_auc']:>7.4f}  {block['best_params']}"
            )
    print(
        f"\nbest_model={metrics['best_model']}  "
        f"active_feature_set={metrics['active_feature_set']}"
    )


def check_artifact_sizes() -> dict:
    """Return ``{filename: size_mb}`` and flag anything at/above the limit."""
    sizes = {}
    for path in sorted(MODELS_DIR.glob("*")):
        if not path.is_file():
            continue
        size_mb = path.stat().st_size / (1024 * 1024)
        sizes[path.name] = round(size_mb, 2)
        if size_mb >= MAX_ARTIFACT_MB:
            print(
                f"WARNING: {path.name} is {size_mb:.2f} MB, "
                f"which is over the {MAX_ARTIFACT_MB} MB limit."
            )
    return sizes


def suspicious_accuracies(metrics: dict) -> list[tuple[str, str, float]]:
    flagged = []
    for model in MODEL_ORDER:
        for feature_set in FEATURE_ORDER:
            acc = metrics["models"][model][feature_set]["accuracy"]
            if acc > 0.99:
                flagged.append((model, feature_set, acc))
    return flagged
