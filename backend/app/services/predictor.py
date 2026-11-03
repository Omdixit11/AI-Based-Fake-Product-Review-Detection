"""Prediction singleton: load the committed artifacts once, then classify.

Parity rule (Phase 3 spec section 3): preprocessing and feature engineering
are *imported* from ``backend/ml`` and never re-implemented here, so inference
always sees the exact same token stream the models were trained on.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import scipy.sparse as sp

# --- the only allowed source of preprocessing / feature logic ---
from ml.features import build_features
from ml.preprocess import clean_text

from app.config import (
    METRICS_PATH,
    NB_MODEL_PATH,
    SCALER_PATH,
    SVM_LINEAR_PATH,
    SVM_MODEL_PATH,
    VECTORIZER_PATH,
    settings,
)
from app.services import explain, flags, sentiment

TRAINING_COMMAND = "cd backend && python -m ml.run_pipeline"

# Rows per chunk for batch analysis: keeps peak memory low on small machines
# while still using vectorised transform/predict instead of a per-row loop.
BATCH_CHUNK_ROWS = 256

ARTIFACTS: tuple[tuple[str, Path], ...] = (
    ("vectorizer", VECTORIZER_PATH),
    ("scaler", SCALER_PATH),
    ("nb_model", NB_MODEL_PATH),
    ("svm_model", SVM_MODEL_PATH),
    ("svm_linear_base", SVM_LINEAR_PATH),
    ("metrics", METRICS_PATH),
)


class ModelArtifactError(RuntimeError):
    """A trained artifact is missing or unreadable - raised with a fix command."""

    def __init__(self, name: str, path: Path, reason: str = "not found") -> None:
        self.name = name
        self.path = Path(path)
        self.reason = reason
        super().__init__(self.friendly_message())

    def friendly_message(self) -> str:
        relative = self.path.name
        return (
            f"Required model artifact '{relative}' ({self.path}) is {self.reason}. "
            f"Phase 2 must produce it: run  {TRAINING_COMMAND}  and commit the files "
            f"in backend/models/."
        )


@dataclass
class Prediction:
    """One analysis, before it is turned into API JSON (adds id/created_at)."""

    verdict: str
    fake_probability: float
    confidence: float
    model_used: str
    sentiment: dict
    flags: list[dict] = field(default_factory=list)
    tokens: list[dict] = field(default_factory=list)
    token_map: dict[str, list[str]] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    latency_ms: int = 0
    created_at: str = ""
    review_text: str = ""


class Predictor:
    """Loads every artifact exactly once and answers prediction requests."""

    def __init__(self) -> None:
        self.vectorizer = None
        self.scaler = None
        self.models: dict[str, Any] = {}
        self.svm_linear_base = None
        self.metrics: dict[str, Any] = {}
        self.feature_names: Sequence[str] = ()
        self._loaded = False

    # ------------------------------------------------------------------ setup
    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def models_dir(self) -> Path:
        return Path(METRICS_PATH).parent

    @property
    def best_model(self) -> str:
        return str(self.metrics.get("best_model", "svm"))

    @property
    def active_feature_set(self) -> str:
        return str(self.metrics.get("active_feature_set", "tfidf_sentiment"))

    def load(self, force: bool = False) -> "Predictor":
        if self._loaded and not force:
            return self
        for name, path in ARTIFACTS:
            if not Path(path).exists():
                raise ModelArtifactError(name, path, "not found")
        try:
            self.metrics = json.loads(Path(METRICS_PATH).read_text(encoding="utf-8"))
            self.vectorizer = joblib.load(VECTORIZER_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            self.models = {
                "nb": joblib.load(NB_MODEL_PATH),
                "svm": joblib.load(SVM_MODEL_PATH),
            }
            self.svm_linear_base = joblib.load(SVM_LINEAR_PATH)
        except ModelArtifactError:
            raise
        except Exception as exc:  # unreadable / wrong scikit-learn version
            raise ModelArtifactError(
                "artifact set",
                Path(METRICS_PATH),
                f"cannot be loaded ({type(exc).__name__}: {exc}). Reinstall the pinned "
                f"packages with  pip install -r backend/requirements.txt",
            ) from exc
        self.feature_names = self.vectorizer.get_feature_names_out()
        self._validate_metrics()
        self._warm_up()
        self._loaded = True
        return self

    def _warm_up(self) -> None:
        """First predict on a fresh process is slow (BLAS/SVM init, ~3s here).

        Run one throwaway prediction per model during startup so the first
        user request meets the <100 ms target.
        """
        sample = ["nice hotel with a great view"]
        try:
            matrix = self._matrix(sample)
            for model in self.models.values():
                model.predict_proba(matrix)
            self._explain(self.best_model, matrix, sample[0])
        except Exception:  # never let warm-up break startup
            pass

    def _validate_metrics(self) -> None:
        for key in ("best_model", "active_feature_set"):
            if key not in self.metrics:
                raise ModelArtifactError(
                    "metrics", Path(METRICS_PATH), f"is missing the '{key}' key"
                )
        if self.best_model not in ("nb", "svm"):
            raise ModelArtifactError(
                "metrics", Path(METRICS_PATH), f"has an unknown best_model {self.best_model!r}"
            )

    def reset(self) -> None:
        """Drop everything (tests use this to re-read FAKE_LABEL / artifacts)."""
        self.vectorizer = None
        self.scaler = None
        self.models = {}
        self.svm_linear_base = None
        self.metrics = {}
        self.feature_names = ()
        self._loaded = False

    # --------------------------------------------------------------- inference
    def resolve_model(self, choice: str | None) -> str:
        requested = (choice or "best").strip().lower()
        if requested == "best":
            return self.best_model
        if requested not in self.models:
            raise ValueError(f"Unknown model {choice!r}; use 'best', 'nb' or 'svm'.")
        return requested

    def _fitted_objects(self) -> dict:
        return {"vectorizer": self.vectorizer, "scaler": self.scaler}

    def fake_column(self, model) -> int:
        """Column of ``predict_proba`` that holds the fake probability."""
        classes = list(model.classes_)
        fake_idx = explain.fake_genuine_indices(classes, settings.fake_label)[0]
        return int(fake_idx)

    def _matrix(self, texts: list[str]) -> Any:
        return build_features(texts, self._fitted_objects(), self.active_feature_set)

    def _fake_probabilities(self, model, matrix) -> np.ndarray:
        proba = np.asarray(model.predict_proba(matrix), dtype=float)
        return proba[:, self.fake_column(model)]

    def predict_one(
        self,
        review: str,
        model_choice: str = "best",
        rating: int | None = None,
        with_explanation: bool = True,
    ) -> Prediction:
        self.load()
        started = time.perf_counter()
        name = self.resolve_model(model_choice)
        model = self.models[name]

        matrix = self._matrix([review])
        fake_prob = float(self._fake_probabilities(model, matrix)[0])
        verdict = "fake" if fake_prob >= 0.5 else "genuine"
        confidence = max(fake_prob, 1.0 - fake_prob)

        senti = sentiment.analyze(review)
        meta = flags.count_meta(review)

        token_rows: list[dict] = []
        token_map: dict[str, list[str]] = {}
        if with_explanation:
            token_rows, token_map = self._explain(name, matrix, review)

        latency_ms = int((time.perf_counter() - started) * 1000)
        return Prediction(
            verdict=verdict,
            fake_probability=round(fake_prob, 6),
            confidence=round(confidence, 6),
            model_used=name,
            sentiment=senti,
            flags=flags.detect_flags(review, senti, rating, meta),
            tokens=token_rows,
            token_map=token_map,
            meta=meta,
            latency_ms=max(latency_ms, 1),
            created_at=_iso_now(),
            review_text=review,
        )

    def predict_many(
        self,
        reviews: list[str],
        model_choice: str = "best",
        ratings: Sequence[int | None] | None = None,
    ) -> list[Prediction]:
        """Vectorised batch scoring: one transform + one predict_proba per chunk."""
        self.load()
        name = self.resolve_model(model_choice)
        model = self.models[name]
        count = len(reviews)
        if ratings is None or len(ratings) != count:
            ratings = [None] * count
        results: list[Prediction | None] = [None] * count

        for start in range(0, count, BATCH_CHUNK_ROWS):
            chunk = reviews[start : start + BATCH_CHUNK_ROWS]
            chunk_ratings = list(ratings)[start : start + BATCH_CHUNK_ROWS]
            matrix = self._matrix(chunk)
            fake_probs = self._fake_probabilities(model, matrix)
            senti_rows = sentiment.analyze_many(chunk)
            for offset, review in enumerate(chunk):
                started = time.perf_counter()
                fake_prob = float(fake_probs[offset])
                verdict = "fake" if fake_prob >= 0.5 else "genuine"
                results[start + offset] = Prediction(
                    verdict=verdict,
                    fake_probability=round(fake_prob, 6),
                    confidence=round(max(fake_prob, 1.0 - fake_prob), 6),
                    model_used=name,
                    sentiment=senti_rows[offset],
                    flags=flags.detect_flags(
                        review, senti_rows[offset], chunk_ratings[offset]
                    ),
                    meta=flags.count_meta(review),
                    latency_ms=max(
                        int((time.perf_counter() - started) * 1000), 1
                    ),
                    created_at=_iso_now(),
                    review_text=review,
                )
        return [prediction for prediction in results if prediction is not None]

    def _explain(
        self, name: str, matrix, review: str
    ) -> tuple[list[dict], dict[str, list[str]]]:
        """Top contributing tokens for this review + their surface words."""
        try:
            if name == "nb":
                scores = explain.nb_score_vector(self.models["nb"], settings.fake_label)
            else:
                scores = explain.svm_score_vector(
                    self.svm_linear_base, settings.fake_label
                )
        except ValueError:
            return [], {}
        row = matrix[0] if sp.issparse(matrix) else np.asarray(matrix)[0:1]
        tokens = explain.top_contributions(
            scores, row, self.feature_names, settings.max_tokens_returned
        )
        surface = explain.surface_map(review)
        return tokens, explain.expand_to_surface(tokens, surface)


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


# Module-level singleton used by the routers and the lifespan handler.
predictor = Predictor()

# Parity guarantee: these names are re-exported so the API surface and the ML
# package share the very same function objects (asserted by tests).
__all__ = ["predictor", "clean_text", "build_features", "Prediction", "ModelArtifactError"]
