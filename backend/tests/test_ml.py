"""Phase 2 tests. They never need the raw dataset, only the committed artifacts."""
from __future__ import annotations

import json

import joblib
import numpy as np
import pytest

from ml.config import (
    METRICS_PATH,
    NB_MODEL_PATH,
    SCALER_PATH,
    SVM_LINEAR_PATH,
    SVM_MODEL_PATH,
    VECTORIZER_PATH,
)
from ml.features import build_features, fit_feature_extractors
from ml.preprocess import clean_text, load_dataset

TINY_TEXTS = [
    "great hotel room with great view",
    "terrible hotel room and rude staff",
    "not a good hotel room at all",
    "amazing hotel with friendly staff",
    "no hot water in the room",
    "bad hotel room never again",
]


def test_clean_text_keeps_negations():
    tokens = clean_text("This is not good and we will never return.").split()
    assert "not" in tokens
    assert "never" in tokens


def test_clean_text_removes_urls_and_html():
    cleaned = clean_text("Visit https://example.com now <b>wow</b>")
    assert "http" not in cleaned
    assert "example" not in cleaned
    assert "wow" in cleaned


def test_clean_text_removes_digits_and_is_deterministic():
    text = "Room 123 was 4/5 stars, really GREAT!!!"
    first = clean_text(text)
    second = clean_text(text)
    assert first == second
    assert not any(ch.isdigit() for ch in first)
    assert first == first.lower()


def test_feature_matrix_has_same_columns_at_inference():
    fitted = fit_feature_extractors(TINY_TEXTS)
    for feature_set in ("tfidf_only", "tfidf_sentiment"):
        train_matrix = build_features(TINY_TEXTS, fitted, feature_set)
        new_matrix = build_features(["A brand new review with a view"], fitted, feature_set)
        assert train_matrix.shape[1] == new_matrix.shape[1]
        assert new_matrix.shape[0] == 1
        if feature_set == "tfidf_sentiment":
            # Naive Bayes needs non-negative values.
            assert new_matrix.min() >= 0.0


def test_load_dataset_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "does_not_exist.csv", verbose=False)


def test_artifacts_exist_and_load():
    for path in (
        VECTORIZER_PATH,
        SCALER_PATH,
        NB_MODEL_PATH,
        SVM_MODEL_PATH,
        SVM_LINEAR_PATH,
    ):
        assert path.exists(), f"missing artifact: {path}"
        assert joblib.load(path) is not None
    assert METRICS_PATH.exists()


def test_saved_models_predict_proba_sums_to_one():
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    fitted = {
        "vectorizer": joblib.load(VECTORIZER_PATH),
        "scaler": joblib.load(SCALER_PATH),
    }
    X = build_features(
        ["The room was clean and the staff were friendly.", "Fake five star review!!!"],
        fitted,
        metrics["active_feature_set"],
    )
    for path in (NB_MODEL_PATH, SVM_MODEL_PATH):
        model = joblib.load(path)
        proba = model.predict_proba(X)
        assert proba.shape == (2, 2)
        assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-6)

    linear = joblib.load(SVM_LINEAR_PATH)
    assert linear.coef_.shape[1] == X.shape[1]


def test_metrics_json_contract():
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    for key in ("generated_at", "dataset", "best_model", "active_feature_set", "models"):
        assert key in metrics
    for key in ("name", "size", "train_size", "test_size", "fake_percent", "avg_words"):
        assert key in metrics["dataset"]
    assert "synthetic" not in metrics["dataset"]["name"].lower()
    assert metrics["best_model"] in ("nb", "svm")
    assert metrics["active_feature_set"] in ("tfidf_only", "tfidf_sentiment")

    for model in ("nb", "svm"):
        for feature_set in ("tfidf_only", "tfidf_sentiment"):
            block = metrics["models"][model][feature_set]
            for key in (
                "accuracy",
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "confusion_matrix",
                "roc_curve",
                "best_params",
            ):
                assert key in block
            assert len(block["confusion_matrix"]) == 2
            assert all(len(row) == 2 for row in block["confusion_matrix"])
            assert len(block["roc_curve"]["fpr"]) == len(block["roc_curve"]["tpr"])
            assert len(block["roc_curve"]["fpr"]) <= 100
