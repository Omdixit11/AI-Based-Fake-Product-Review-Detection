"""Explainability: which vocabulary items pushed the model toward fake/genuine.

Two sources, exactly as specified in the Phase 3 spec section 5:

* Naive Bayes - ``feature_log_prob_[fake] - feature_log_prob_[genuine]``
* SVM         - the coefficients of ``svm_linear_base.pkl`` (the readable
                linear twin of the calibrated model)

Only items actually present in the reviewed text are scored, and each token is
mapped back to the surface words of the original review so the frontend can
highlight them (``clean_text`` lemmatizes, so "amazing" becomes "amaze").
"""
from __future__ import annotations

import re
from typing import Sequence

import numpy as np
from scipy import sparse

from ml.preprocess import clean_text

_WORD_RE = re.compile(r"[A-Za-z']+")
_MAX_SURFACE_WORDS = 6


def nb_score_vector(model, fake_label: int) -> np.ndarray:
    """Log-probability difference (fake minus genuine) per vocabulary column."""
    log_prob = np.asarray(model.feature_log_prob_, dtype=float)
    fake_idx, genuine_idx = fake_genuine_indices(model.classes_, fake_label)
    return log_prob[fake_idx] - log_prob[genuine_idx]


def svm_score_vector(linear_model, fake_label: int) -> np.ndarray:
    """Linear SVM coefficients, signed so that positive always means fake."""
    coef = np.asarray(linear_model.coef_, dtype=float)
    classes = list(linear_model.classes_)
    fake_idx, genuine_idx = fake_genuine_indices(classes, fake_label)
    if coef.ndim == 1 or coef.shape[0] == 1:
        # Binary one-vs-one layout: the single row separates classes[1] from
        # classes[0], so it must be flipped when the fake label sits on the
        # negative side (e.g. a swapped FAKE_LABEL).
        row = coef.reshape(-1)
        return row if fake_idx == 1 else -row
    return coef[fake_idx] - coef[genuine_idx]


def fake_genuine_indices(classes: Sequence, fake_label: int) -> tuple[int, int]:
    """Position of the fake class and of the other class in ``model.classes_``."""
    if len(list(classes)) != 2:
        raise ValueError(
            f"Expected a binary classifier, found classes {list(classes)}."
        )
    fake_idx = _index_of(classes, fake_label)
    if fake_idx is None:
        raise ValueError(
            f"Model classes {list(classes)} contain no column for FAKE_LABEL="
            f"{fake_label}; check FAKE_LABEL in backend/app/config.py."
        )
    genuine_idx = 1 - fake_idx
    return fake_idx, genuine_idx


def _index_of(classes: Sequence, label: int) -> int | None:
    for position, value in enumerate(classes):
        if int(value) == int(label):
            return position
    return None


def top_contributions(
    score_vector: np.ndarray,
    feature_row,
    feature_names: Sequence[str],
    limit: int = 8,
) -> list[dict]:
    """Top ``limit`` vocabulary items by |score| among the ones present."""
    row = feature_row.tocsr() if sparse.issparse(feature_row) else sparse.csr_matrix(row_array(feature_row))
    indices = np.asarray(row.indices, dtype=int)
    if indices.size == 0:
        return []
    weights = np.asarray(row.data, dtype=float)
    scores = np.asarray(score_vector, dtype=float)[indices] * weights
    order = np.argsort(-np.abs(scores))[: max(0, int(limit))]
    out: list[dict] = []
    for position in order:
        index = int(indices[int(position)])
        score = float(scores[int(position)])
        if score == 0.0:
            continue
        out.append(
            {
                "token": str(feature_names[index]),
                "score": round(score, 4),
                "direction": "fake" if score > 0 else "genuine",
            }
        )
    return out


def row_array(values) -> np.ndarray:
    """Dense-safe conversion for a single feature row."""
    return np.asarray(values, dtype=float).reshape(1, -1)


def surface_map(text: str) -> dict[str, list[str]]:
    """cleaned token -> original surface words (what the UI should highlight)."""
    mapping: dict[str, list[str]] = {}
    for raw_word in _WORD_RE.findall(text or ""):
        word = raw_word.strip("'")
        if not word:
            continue
        cleaned = clean_text(word)
        if not cleaned:
            continue
        for token in cleaned.split():
            bucket = mapping.setdefault(token, [])
            if len(bucket) >= _MAX_SURFACE_WORDS:
                continue
            if any(existing.lower() == word.lower() for existing in bucket):
                continue
            bucket.append(word)
    return mapping


def expand_to_surface(tokens: list[dict], mapping: dict[str, list[str]]) -> dict[str, list[str]]:
    """Surface words for the returned tokens (handles unigrams and bigrams)."""
    result: dict[str, list[str]] = {}
    for entry in tokens:
        words: list[str] = []
        for part in str(entry["token"]).split():
            for word in mapping.get(part, []):
                if word not in words:
                    words.append(word)
        result[entry["token"]] = words
    return result
