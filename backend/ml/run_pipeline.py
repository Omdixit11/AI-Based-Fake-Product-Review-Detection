"""One-command ML pipeline: load -> split -> features -> train -> evaluate -> save.

Run from the ``backend/`` folder:

    python -m ml.run_pipeline
"""
from __future__ import annotations

from datetime import datetime, timezone

import joblib
import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split

from .config import (
    DATASET_NAME,
    DATASET_PATH,
    FEATURE_SETS,
    METRICS_PATH,
    MODELS_DIR,
    NB_MODEL_PATH,
    RANDOM_STATE,
    SCALER_PATH,
    SVM_LINEAR_PATH,
    SVM_MODEL_PATH,
    TEST_SIZE,
    VECTORIZER_PATH,
)
from .evaluate import (
    check_artifact_sizes,
    evaluate_model,
    print_summary,
    select_best,
    suspicious_accuracies,
    write_metrics,
)
from .features import build_features, fit_feature_extractors
from .preprocess import load_dataset
from .train_nb import train_naive_bayes
from .train_svm import train_linear_base, train_svm


def _maybe_smote(X, y):
    """Apply SMOTE only when the minority class is below 40 percent."""
    counts = np.bincount(y)
    minority_ratio = counts.min() / counts.sum()
    if minority_ratio >= 0.40:
        return X, y, False
    k = max(1, min(5, int(counts.min()) - 1))
    smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=k)
    X_res, y_res = smote.fit_resample(X, y)
    return X_res, y_res, True


def main() -> dict:
    print("=" * 72)
    print("TruthLens - Phase 2 ML pipeline")
    print("=" * 72)

    df = load_dataset(DATASET_PATH)
    labels = df["label"].to_numpy(dtype=int)
    texts = df["text"].tolist()

    train_texts, test_texts, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=TEST_SIZE,
        stratify=labels,
        random_state=RANDOM_STATE,
    )
    print(
        f"\nStratified split: train={len(train_texts)}, test={len(test_texts)} "
        f"({int(round((1 - TEST_SIZE) * 100))}% / {int(round(TEST_SIZE * 100))}%)"
    )

    # Fit the vectorizer and scaler on the TRAINING split only (no leakage).
    fitted = fit_feature_extractors(train_texts)
    X_train = {fs: build_features(train_texts, fitted, fs) for fs in FEATURE_SETS}
    X_test = {fs: build_features(test_texts, fitted, fs) for fs in FEATURE_SETS}
    for fs in FEATURE_SETS:
        print(f"Feature set {fs:<16} train={X_train[fs].shape} test={X_test[fs].shape}")

    minority_pct = 100.0 * np.bincount(y_train).min() / len(y_train)
    print(f"Minority class in train split: {minority_pct:.2f}%")

    results: dict[tuple[str, str], dict] = {}
    models: dict[str, dict] = {}
    fit_data: dict[str, tuple] = {}

    for fs in FEATURE_SETS:
        X_fit, y_fit, applied = _maybe_smote(X_train[fs], y_train)
        fit_data[fs] = (X_fit, y_fit)
        print(
            f"\n[{fs}] SMOTE: {'applied' if applied else 'skipped'} "
            f"(train rows: {X_fit.shape[0]})"
        )

        print(f"[{fs}] Training Naive Bayes (alpha grid, 5-fold, n_jobs=1)...")
        nb, nb_params, nb_cv = train_naive_bayes(X_fit, y_fit)
        print(f"[{fs}] NB best alpha={nb_params['alpha']} (CV F1={nb_cv:.4f})")

        print(f"[{fs}] Training SVM (C/kernel/gamma grid, 5-fold, n_jobs=1)...")
        svm, svm_params, svm_cv = train_svm(X_fit, y_fit)
        print(f"[{fs}] SVM best params={svm_params} (CV F1={svm_cv:.4f})")
        print(f"[{fs}] SVM calibrated with sigmoid (5-fold).")

        models[fs] = {
            "nb": nb,
            "svm": svm,
            "nb_params": nb_params,
            "svm_params": svm_params,
        }

        for name, model, params in (
            ("nb", nb, nb_params),
            ("svm", svm, svm_params),
        ):
            block = evaluate_model(model, X_test[fs], y_test)
            block["best_params"] = params
            results[(name, fs)] = block

    best_model, active_fs = select_best(results)
    print(f"\nSelected best model: {best_model} with {active_fs} (by F1, then ROC-AUC).")

    # Persist the artifacts that Phases 3-5 load. Both saved models use the
    # same active feature set so the API can switch models without rebuilding.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted["vectorizer"], VECTORIZER_PATH, compress=3)
    joblib.dump(fitted["scaler"], SCALER_PATH, compress=3)
    joblib.dump(models[active_fs]["nb"], NB_MODEL_PATH, compress=3)
    joblib.dump(models[active_fs]["svm"], SVM_MODEL_PATH, compress=3)

    X_fit_active, y_fit_active = fit_data[active_fs]
    linear_base = train_linear_base(
        X_fit_active,
        y_fit_active,
        C=models[active_fs]["svm_params"]["C"],
    )
    joblib.dump(linear_base, SVM_LINEAR_PATH, compress=3)

    fake_percent = 100.0 * float(labels.mean())
    avg_words = float(df["text"].str.split().str.len().mean())
    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": DATASET_NAME,
            "size": int(len(df)),
            "train_size": int(len(train_texts)),
            "test_size": int(len(test_texts)),
            "fake_percent": round(fake_percent, 4),
            "avg_words": round(avg_words, 4),
        },
        "best_model": best_model,
        "active_feature_set": active_fs,
        "models": {
            model: {fs: results[(model, fs)] for fs in FEATURE_SETS}
            for model in ("nb", "svm")
        },
    }
    write_metrics(metrics)
    print(f"\nWrote {METRICS_PATH}")

    print_summary(metrics)

    sizes = check_artifact_sizes()
    print("\nArtifact sizes:")
    for name, size in sizes.items():
        print(f"  {name:<22} {size:>7.2f} MB")

    flagged = suspicious_accuracies(metrics)
    if flagged:
        print("\nSUSPICIOUS: accuracy above 0.99 in:")
        for model, fs, acc in flagged:
            print(f"  - {model} / {fs}: {acc:.4f}")
        dropped = df.attrs.get("duplicates_dropped", "unknown")
        print(
            f"Duplicate texts dropped before splitting: {dropped}. "
            "No source/polarity/hotel columns are used as features, so this is "
            "not label leakage. The Deceptive Opinion Spam Corpus is known to be "
            "highly separable for TF-IDF + linear models; report this honestly."
        )
    else:
        print("\nNo accuracy above 0.99; metrics look plausible.")

    return metrics


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1)
