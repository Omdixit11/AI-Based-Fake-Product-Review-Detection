"""Runtime configuration for the TruthLens API.

Everything that the ML pipeline already decided (artifact paths, the meaning
of the fake label, which feature set is active) is re-exported from
``backend/ml/config.py`` instead of being duplicated here - that is the golden
design rule: training and inference read the same configuration.

Values that are genuinely API-only (request limits, CORS, database URL) are
read from the environment. ``settings`` is a mutable object so tests can flip
a value (for example ``fake_label``) without touching any committed file.
"""
from __future__ import annotations

import os

from ml import config as ml_config

APP_NAME = "TruthLens API"
APP_VERSION = "1.0.0"

# --- artifacts (single source of truth: ml.config) ---
MODELS_DIR = ml_config.MODELS_DIR
VECTORIZER_PATH = ml_config.VECTORIZER_PATH
SCALER_PATH = ml_config.SCALER_PATH
NB_MODEL_PATH = ml_config.NB_MODEL_PATH
SVM_MODEL_PATH = ml_config.SVM_MODEL_PATH
SVM_LINEAR_PATH = ml_config.SVM_LINEAR_PATH
METRICS_PATH = ml_config.METRICS_PATH

# --- feature sets, straight from the ML package ---
FEATURE_SETS = ml_config.FEATURE_SETS

# Training used these labels; the API must map predict_proba columns with the
# same value, never a hard-coded column index.
DEFAULT_FAKE_LABEL = ml_config.FAKE_LABEL

MODEL_CHOICES = ("best", "nb", "svm")
MODEL_NAMES = ("nb", "svm")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _origins_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name) or default
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Settings:
    """Mutable settings bundle (env-driven, patchable in tests)."""

    def __init__(self) -> None:
        # Labels
        self.fake_label: int = _int_env("FAKE_LABEL", DEFAULT_FAKE_LABEL)

        # Request / response limits
        self.min_review_chars: int = 1
        self.max_review_chars: int = _int_env("MAX_REVIEW_CHARS", 5000)
        self.max_batch_rows: int = _int_env("MAX_BATCH_ROWS", 5000)
        self.max_batch_bytes: int = _int_env("MAX_BATCH_BYTES", 5 * 1024 * 1024)
        self.min_rating: int = 1
        self.max_rating: int = 5
        self.max_tokens_returned: int = _int_env("MAX_TOKENS", 8)

        # Storage
        self.database_url: str = os.getenv("DATABASE_URL") or "sqlite:///./history.db"

        # CORS
        self.cors_origins: list[str] = _origins_env(
            "CORS_ORIGINS", "http://localhost:3000"
        )

        # Simple per-IP limiter (see main.py); 0 disables it.
        self.rate_limit_per_minute: int = _int_env("RATE_LIMIT_PER_MINUTE", 300)

        self.history_default_limit: int = _int_env("HISTORY_DEFAULT_LIMIT", 50)
        self.history_max_limit: int = _int_env("HISTORY_MAX_LIMIT", 500)


settings = Settings()


def reload_from_env() -> None:
    """Re-read environment-driven settings (used by tests that need a fresh DB)."""
    fresh = Settings()
    settings.__dict__.update(fresh.__dict__)
