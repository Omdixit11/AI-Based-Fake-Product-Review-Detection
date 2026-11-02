"""Feature engineering: TF-IDF, VADER sentiment and shallow text metadata.

The two feature sets are:

* ``tfidf_only``       - cleaned-text TF-IDF (unigrams + bigrams)
* ``tfidf_sentiment``  - TF-IDF plus 4 VADER scores and 6 meta features,
                         scaled with a train-fitted MinMaxScaler and
                         sparse-hstacked so Naive Bayes stays non-negative.

``build_features`` is used both at training time and by the API at inference
time, which guarantees identical column layouts.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler

from .config import (
    FEATURE_SETS,
    META_FEATURE_NAMES,
    TFIDF_PARAMS,
    VADER_FEATURE_NAMES,
)
from .preprocess import clean_text

EXTRA_FEATURE_NAMES = VADER_FEATURE_NAMES + META_FEATURE_NAMES
_ALPHA_RE = re.compile(r"[A-Za-z']+")


def _texts(texts) -> list[str]:
    if texts is None:
        return []
    return [t if isinstance(t, str) else ("" if t is None else str(t)) for t in texts]


@lru_cache(maxsize=1)
def _vader():
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer

        return SentimentIntensityAnalyzer()
    except LookupError as exc:  # pragma: no cover - environment problem
        raise RuntimeError(
            "NLTK vader_lexicon is missing. Run: python scripts/download_nltk.py"
        ) from exc


def extract_vader(texts) -> np.ndarray:
    """Return an ``(n, 4)`` array: neg, neu, pos, compound on raw text."""
    analyzer = _vader()
    rows = []
    for text in _texts(texts):
        scores = analyzer.polarity_scores(text)
        rows.append(
            [
                scores.get("neg", 0.0),
                scores.get("neu", 0.0),
                scores.get("pos", 0.0),
                scores.get("compound", 0.0),
            ]
        )
    if not rows:
        return np.empty((0, len(VADER_FEATURE_NAMES)), dtype=float)
    return np.asarray(rows, dtype=float)


def extract_meta(texts) -> np.ndarray:
    """Return an ``(n, 6)`` array of shallow features computed on RAW text."""
    rows = []
    for text in _texts(texts):
        words = text.split()
        word_count = len(words)
        alpha_words = [w.strip("'") for w in _ALPHA_RE.findall(text)]
        alpha_words = [w for w in alpha_words if w]
        uppercase_words = sum(1 for w in words if len(w) >= 2 and w.isupper())
        avg_word_length = (
            float(np.mean([len(w) for w in alpha_words])) if alpha_words else 0.0
        )
        rows.append(
            [
                float(len(text)),
                float(word_count),
                float(text.count("!")),
                float(uppercase_words / word_count) if word_count else 0.0,
                1.0 if any(ch.isdigit() for ch in text) else 0.0,
                avg_word_length,
            ]
        )
    if not rows:
        return np.empty((0, len(META_FEATURE_NAMES)), dtype=float)
    return np.asarray(rows, dtype=float)


def _extra_matrix(texts) -> np.ndarray:
    vader = extract_vader(texts)
    meta = extract_meta(texts)
    return np.hstack([vader, meta]).astype(float)


def fit_feature_extractors(train_texts) -> dict:
    """Fit TF-IDF and the extra-feature scaler on the TRAINING split only."""
    texts = _texts(train_texts)
    vectorizer = TfidfVectorizer(**TFIDF_PARAMS)
    vectorizer.fit([clean_text(t) for t in texts])

    scaler = MinMaxScaler()
    scaler.fit(_extra_matrix(texts))

    return {"vectorizer": vectorizer, "scaler": scaler}


def build_features(texts, fitted_objects: dict, feature_set: str = "tfidf_sentiment"):
    """Build a feature matrix with columns identical to training time.

    ``fitted_objects`` must contain the fitted ``vectorizer`` and ``scaler``
    (the scaler is only used by ``tfidf_sentiment``).
    """
    if feature_set not in FEATURE_SETS:
        raise ValueError(
            f"Unknown feature_set {feature_set!r}; expected one of {FEATURE_SETS}."
        )
    vectorizer = fitted_objects["vectorizer"]
    texts = _texts(texts)

    if not texts:
        return sparse.csr_matrix(
            (0, len(vectorizer.get_feature_names_out())), dtype=float
        )

    cleaned = [clean_text(t) for t in texts]
    tfidf = vectorizer.transform(cleaned).astype(float)

    if feature_set == "tfidf_only":
        return tfidf

    scaler = fitted_objects["scaler"]
    extra = scaler.transform(_extra_matrix(texts))
    return sparse.hstack(
        [tfidf, sparse.csr_matrix(extra)], format="csr"
    ).astype(float)
