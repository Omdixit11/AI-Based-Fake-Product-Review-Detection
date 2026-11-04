"""Pydantic v2 request/response models.

Field names mirror docs/LLD.md section 3 exactly - the Next.js frontend is
already built against this contract, so nothing here is renamed or re-cased.
Limits are read from ``settings`` inside the validators so they stay
consistent with the rest of the API.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import MODEL_CHOICES, MODEL_NAMES, settings

Verdict = Literal["fake", "genuine"]
ModelChoice = Literal["best", "nb", "svm"]
ModelUsed = Literal["nb", "svm"]
# ``model_used`` gains a third value when a Tier-1 hard rule decides the
# request without consulting the classifier. The Phase 3 values are unchanged.
ResponseModelUsed = Literal["nb", "svm", "tier1_rules"]
DecisionSource = Literal["model", "tier1_rules"]
Severity = Literal["low", "medium", "high"]
TokenDirection = Literal["fake", "genuine"]
SentimentLabel = Literal["Positive", "Mixed", "Negative"]
Tier1Action = Literal["pass", "flag_spam"]
RuleKind = Literal["soft", "hard"]

# --- error envelope: {"error": {"code": ..., "message": ...}} ---
ERROR_ENVELOPE_EXAMPLE = {"error": {"code": "VALIDATION_ERROR", "message": "..."}}


def error_detail(code: str, message: str) -> dict:
    """Body of an HTTPException.detail that the main.py handler passes through."""
    return {"error": {"code": code, "message": message}}


class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiError(BaseModel):
    error: ErrorDetail


class SentimentBlock(BaseModel):
    compound: float
    label: SentimentLabel
    pos: float
    neu: float
    neg: float


class RedFlag(BaseModel):
    code: str
    label: str
    severity: Severity


class TokenScore(BaseModel):
    token: str
    score: float
    direction: TokenDirection


class PredictionMeta(BaseModel):
    words: int
    exclamations: int
    caps_words: int


MAX_USER_ID_CHARS = 128
MAX_REVIEWS_LAST_MINUTE = 10_000


class PredictMetadata(BaseModel):
    """Optional Tier-1 context for ``POST /api/predict`` (Phase 3.5, additive).

    Every field is optional and a request without ``metadata`` behaves exactly
    as it did before. Limits exist so a client cannot make the in-memory
    tracker meaningless with an absurd number.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str | None = None
    posted_at: datetime | None = None
    reviews_last_minute: int | None = None

    @field_validator("user_id")
    @classmethod
    def _user_id_length(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("'metadata.user_id' must not be blank.")
        if len(stripped) > MAX_USER_ID_CHARS:
            raise ValueError(
                f"'metadata.user_id' is too long: {len(stripped)} characters, "
                f"maximum is {MAX_USER_ID_CHARS}."
            )
        return stripped

    @field_validator("reviews_last_minute")
    @classmethod
    def _reviews_sane(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("'metadata.reviews_last_minute' cannot be negative.")
        if value > MAX_REVIEWS_LAST_MINUTE:
            raise ValueError(
                f"'metadata.reviews_last_minute' must be at most "
                f"{MAX_REVIEWS_LAST_MINUTE}."
            )
        return int(value)

    @field_validator("posted_at")
    @classmethod
    def _assume_utc(cls, value: datetime | None) -> datetime | None:
        """Naive timestamps are UTC, matching the rest of the API."""
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Tier1Rule(BaseModel):
    code: str
    label: str
    severity: Severity
    kind: RuleKind


class Tier1Block(BaseModel):
    """Result of the rule filter that runs before the model."""

    triggered: bool
    action: Tier1Action
    rules: list[Tier1Rule] = Field(default_factory=list)


class SarcasmBlock(BaseModel):
    """Optional risk signal; never changes the verdict.

    ``risk_level`` / cue lists stay None (and are therefore omitted) when
    nothing was suspected, per the Phase 3.5 response shape.
    """

    suspected: bool
    score: float
    risk_level: Severity | None = None
    positive_cues: list[str] | None = None
    negative_cues: list[str] | None = None


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review: str
    rating: int | None = None
    model: str = "best"
    # Optional Tier-1 context (Phase 3.5). Absent means "no behaviour signals".
    metadata: PredictMetadata | None = None

    @field_validator("review")
    @classmethod
    def _review_length(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"'review' must be a non-empty string (1-{settings.max_review_chars} characters)."
            )
        if len(value) > settings.max_review_chars:
            raise ValueError(
                f"'review' is too long: {len(value)} characters, maximum is "
                f"{settings.max_review_chars}."
            )
        return value

    @field_validator("rating")
    @classmethod
    def _rating_range(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if not settings.min_rating <= int(value) <= settings.max_rating:
            raise ValueError(
                f"'rating' must be between {settings.min_rating} and "
                f"{settings.max_rating}."
            )
        return int(value)

    @field_validator("model")
    @classmethod
    def _known_model(cls, value: str) -> str:
        if value not in MODEL_CHOICES:
            raise ValueError(
                f"'model' must be one of {list(MODEL_CHOICES)}, got {value!r}."
            )
        return value


class PredictionResponse(BaseModel):
    """POST /api/predict response."""

    # ``model_used`` legitimately starts with pydantic's protected "model_"
    # prefix; the contract in docs/LLD.md fixes the name, so opt out here.
    model_config = ConfigDict(protected_namespaces=())

    id: int
    verdict: Verdict
    fake_probability: float
    confidence: float
    model_used: ResponseModelUsed
    sentiment: SentimentBlock
    flags: list[RedFlag] = Field(default_factory=list)
    tokens: list[TokenScore] = Field(default_factory=list)
    meta: PredictionMeta
    latency_ms: int
    created_at: str

    # Additive (not part of the LLD contract, so the frontend can ignore it):
    # maps each cleaned token back to the surface words in the review so the
    # analyzer can highlight them. Requested by Phase 3 spec section 5.
    token_map: dict[str, list[str]] = Field(default_factory=dict)

    # Phase 3.5 optional fields. The route serialises with
    # ``response_model_exclude_none``, so while the feature switches are off
    # these keys are absent entirely and the body is the Phase 3 body.
    tier1: Tier1Block | None = None
    sarcasm: SarcasmBlock | None = None
    decision_source: DecisionSource | None = None


class BatchRow(BaseModel):
    row: int
    review: str
    rating: int | None = None
    verdict: Verdict
    fake_probability: float
    confidence: float
    sentiment_label: SentimentLabel


class BatchSummary(BaseModel):
    total: int
    fake_count: int
    fake_percent: float
    avg_confidence: float


class BatchResponse(BaseModel):
    rows: list[BatchRow] = Field(default_factory=list)
    summary: BatchSummary


class ModelInfo(BaseModel):
    """GET /api/models."""

    models: list[ModelUsed] = Field(default_factory=list)
    default: ModelChoice = "best"
    best_model: ModelUsed = "svm"
    active_feature_set: str = "tfidf_only"


class HistoryEntry(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int
    review_text: str
    verdict: str
    fake_probability: float
    model_used: str
    compound: float
    flags_json: str
    tokens_json: str
    created_at: str


class HistoryListResponse(BaseModel):
    total: int
    entries: list[HistoryEntry] = Field(default_factory=list)
    # Alias of ``entries``: the Phase 3 prompt calls the collection "items",
    # the committed frontend reads "entries". Both carry the same array.
    items: list[HistoryEntry] = Field(default_factory=list)


class DeletedResponse(BaseModel):
    deleted: int
    id: int | None = None


class ClearedResponse(BaseModel):
    deleted: int


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    version: str


KNOWN_MODELS = list(MODEL_NAMES)
