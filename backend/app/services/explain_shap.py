"""On-demand explanations for one review: SHAP (linear SVM) or log-probability (NB).

Phase 3.5 feature 3. ``POST /api/explain`` is deliberately separate from
``/api/predict`` so the prediction hot path never pays for explanation work it
does not need.

What "SHAP" means here, stated honestly
---------------------------------------
The committed linear model is ``LinearSVC`` - a *linear* model - and the
background is an all-zero TF-IDF row. For a linear model with a zero background
the Shapley value of feature *j* is exactly ``coef[j] * x[j]``, and the base
value is ``f(0)``, i.e. the intercept. So both code paths below produce the
same numbers:

* ``shap.LinearExplainer`` (lazy import - the app runs without the package);
* the direct computation ``coef * tfidf``, used when ``shap`` is missing, when
  ``ENABLE_SHAP`` is false, or if the explainer raises (it has been observed to
  hit ``NotImplementedError`` on sparse coefficients in other versions).

Naive Bayes is **not** SHAP. Its per-token contribution is the
``feature_log_prob_[fake] - feature_log_prob_[genuine]`` difference times the
term weight, which is what the Phase 3 explain service already computed; the
method label says ``naive-bayes-logprob`` so nothing is overclaimed. There the
``base_value`` is the class log-prior difference, the constant term of the same
additive log-odds decomposition.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np
import scipy.sparse as sp

from app.config import settings
from app.services import explain

METHOD_SHAP_LINEAR = "shap-linear"
METHOD_NB_LOGPROB = "naive-bayes-logprob"
METHOD_LINEAR_COEFFICIENTS = "linear-coefficients"

# Spec section 3.3: the explain endpoint shows more tokens than /api/predict.
TOP_TOKENS = 10


def _load_shap():
    """Import ``shap`` lazily, or return None when it is not installed.

    Nothing in this module imports shap at module level, so the API starts and
    every other feature works on a machine that never installed the optional
    requirement. Tests monkeypatch this one function to exercise both paths.
    """
    try:
        import shap  # type: ignore
    except Exception:  # pragma: no cover - ImportError and any import-time failure
        return None
    return shap


def shap_available() -> bool:
    """True when the optional package can be imported *and* is switched on."""
    return bool(settings.enable_shap) and _load_shap() is not None


def _fake_side_sign(model, fake_label: int) -> int:
    """+1 when the model's positive direction already means "fake"."""
    fake_idx, _ = explain.fake_genuine_indices(list(model.classes_), fake_label)
    return 1 if fake_idx == 1 else -1


def _row_dense(matrix) -> np.ndarray:
    if sp.issparse(matrix):
        return np.asarray(matrix.todense(), dtype=float).ravel()
    return np.asarray(matrix, dtype=float).reshape(-1)


def _shap_values(shap_module, model, matrix) -> tuple[np.ndarray, float]:
    """LinearExplainer on a sparse all-zero background row."""
    background = sp.csr_matrix((1, matrix.shape[1]), dtype=float)
    explainer = shap_module.LinearExplainer(model, background)
    values = np.asarray(explainer.shap_values(matrix), dtype=float)
    while values.ndim > 2:
        values = values[0]
    if values.ndim == 2:
        values = values[0]
    expected = getattr(explainer, "expected_value", None)
    if expected is None:  # pragma: no cover - defensive
        base = float(np.ravel(model.intercept_)[0])
    else:
        base = float(np.ravel(np.asarray(expected, dtype=float))[0])
    return values.ravel(), base


def _direct_values(model, matrix, fake_label: int) -> tuple[np.ndarray, float]:
    """Identical math without the library: coef * tfidf, base = f(0)."""
    scores = explain.svm_score_vector(model, fake_label)
    values = scores * _row_dense(matrix)
    intercept = np.ravel(np.asarray(model.intercept_, dtype=float))
    return values, float(intercept[0]) if intercept.size else 0.0


def _top_from_values(
    values: np.ndarray, matrix, feature_names, limit: int = TOP_TOKENS
) -> list[dict]:
    """Rank the vocabulary items actually present by absolute contribution."""
    row = matrix[0] if sp.issparse(matrix) else matrix
    row = row.tocsr() if sp.issparse(row) else sp.csr_matrix(np.asarray(row, dtype=float))
    indices = np.asarray(row.indices, dtype=int)
    if indices.size == 0:
        return []
    present = [
        (int(index), float(values[int(index)]))
        for index in indices
        if int(index) < values.size and values[int(index)] != 0.0
    ]
    present.sort(key=lambda pair: -abs(pair[1]))
    return [
        {
            "token": str(feature_names[index]),
            "score": round(score, 4),
            "direction": "fake" if score > 0 else "genuine",
        }
        for index, score in present[: max(0, int(limit))]
    ]


def explain_svm(review: str, predictor_obj: Any) -> dict[str, Any]:
    """Token contributions for the linear SVM, via shap when possible."""
    matrix = predictor_obj._matrix([review])
    model = predictor_obj.svm_linear_base
    fake_label = int(settings.fake_label)

    shap_module = _load_shap() if settings.enable_shap else None
    values = None
    base_value = 0.0
    method = METHOD_LINEAR_COEFFICIENTS
    if shap_module is not None:
        try:
            values, base_value = _shap_values(shap_module, model, matrix)
            method = METHOD_SHAP_LINEAR
        except Exception:  # NotImplementedError, shape problems, ... (any version)
            values = None

    if values is not None:
        # shap returns values in decision_function space, which separates
        # classes[1] from classes[0]; re-orient so positive always means fake.
        values = values * _fake_side_sign(model, fake_label)
    else:
        values, base_value = _direct_values(model, matrix, fake_label)
        # svm_score_vector is already signed towards "fake", so no flip here.
        # Same value as SHAP, computed directly: still a SHAP explanation while
        # the switch is on and the library merely failed (spec section 3.3).
        method = METHOD_SHAP_LINEAR if shap_module is not None else method

    tokens = _top_from_values(values, matrix, predictor_obj.feature_names)
    surface = explain.surface_map(review)
    return {
        "method": method,
        "model_used": "svm",
        "base_value": round(base_value, 6),
        "tokens": tokens,
        "token_map": explain.expand_to_surface(tokens, surface),
    }


def explain_nb(review: str, predictor_obj: Any) -> dict[str, Any]:
    """Log-probability differences for Naive Bayes (labelled honestly)."""
    matrix = predictor_obj._matrix([review])
    model = predictor_obj.models["nb"]
    fake_label = int(settings.fake_label)

    scores = explain.nb_score_vector(model, fake_label)
    values = scores * _row_dense(matrix)

    log_prior = np.asarray(model.class_log_prior_, dtype=float)
    fake_idx, genuine_idx = explain.fake_genuine_indices(list(model.classes_), fake_label)
    base_value = float(log_prior[fake_idx] - log_prior[genuine_idx])

    tokens = _top_from_values(values, matrix, predictor_obj.feature_names)
    surface = explain.surface_map(review)
    return {
        "method": METHOD_NB_LOGPROB,
        "model_used": "nb",
        "base_value": round(base_value, 6),
        "tokens": tokens,
        "token_map": explain.expand_to_surface(tokens, surface),
    }


def explain_review(
    review: str, model_choice: str = "best", predictor_obj: Any = None
) -> dict[str, Any]:
    """Build the ``POST /api/explain`` body for one review."""
    if predictor_obj is None:  # imported here to keep this module dependency-light
        from app.services.predictor import predictor as singleton

        predictor_obj = singleton

    started = time.perf_counter()
    predictor_obj.load()
    name = predictor_obj.resolve_model(model_choice)
    if name == "nb":
        result = explain_nb(review, predictor_obj)
    else:
        result = explain_svm(review, predictor_obj)
    result["latency_ms"] = max(int((time.perf_counter() - started) * 1000), 1)
    return result


__all__ = [
    "explain_review",
    "explain_svm",
    "explain_nb",
    "shap_available",
    "METHOD_SHAP_LINEAR",
    "METHOD_NB_LOGPROB",
    "METHOD_LINEAR_COEFFICIENTS",
    "TOP_TOKENS",
]
