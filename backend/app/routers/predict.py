"""Prediction endpoints: POST /api/predict and POST /api/predict/batch."""
from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import ValidationError

from app.config import settings
from app.db.database import session_scope
from app.db.models import History
from app.schemas import (
    BatchResponse,
    BatchRow,
    BatchSummary,
    PredictionResponse,
    PredictRequest,
    error_detail,
)
from app.services import sarcasm, tier1
from app.services.predictor import ModelArtifactError, predictor

router = APIRouter(prefix="/api", tags=["predict"])

MAX_ERROR_ROWS_SHOWN = 5


def _prediction_to_response(review: str, prediction, entry_id: int) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": entry_id,
        "verdict": prediction.verdict,
        "fake_probability": prediction.fake_probability,
        "confidence": prediction.confidence,
        "model_used": prediction.model_used,
        "sentiment": prediction.sentiment,
        "flags": prediction.flags,
        "tokens": prediction.tokens,
        "meta": prediction.meta,
        "latency_ms": prediction.latency_ms,
        "created_at": prediction.created_at,
        "token_map": prediction.token_map,
    }
    # Phase 3.5: new keys appear only while the matching switch is on, so a
    # response built with everything off is the Phase 3 response, key for key.
    if settings.enable_tier1:
        body["tier1"] = prediction.tier1 or tier1.empty_result()
        body["decision_source"] = prediction.decision_source
    if settings.enable_sarcasm and prediction.sarcasm is not None:
        body["sarcasm"] = prediction.sarcasm
    return body


def _save_history(review: str, prediction) -> int:
    """Persist one analysis and return its id (LLD section 4 table)."""
    import json

    with session_scope() as session:
        row = History(
            review_text=review,
            verdict=prediction.verdict,
            fake_probability=prediction.fake_probability,
            model_used=prediction.model_used,
            compound=float(prediction.sentiment.get("compound", 0.0)),
            flags_json=json.dumps(prediction.flags),
            tokens_json=json.dumps(prediction.tokens),
        )
        # Keep the stored timestamp identical to the one in the response.
        from datetime import datetime

        try:
            row.created_at = datetime.fromisoformat(prediction.created_at)
        except ValueError:  # pragma: no cover - defensive
            pass
        session.add(row)
        session.flush()
        return int(row.id)


@router.post(
    "/predict",
    response_model=PredictionResponse,
    # Off switches leave tier1/sarcasm/decision_source as None, and None fields
    # are then absent from the JSON - the Phase 3 key set, unchanged.
    response_model_exclude_none=True,
    summary="Analyze a single review",
    responses={
        400: {"model": None, "description": "Invalid review payload"},
        422: {"model": None, "description": "Validation error"},
        503: {"model": None, "description": "Models not loaded"},
    },
)
def predict(payload: PredictRequest) -> dict[str, Any]:
    """Classify one review, explain it, and store it in the history.

    Order (Phase 3.5): Tier-1 rules, then the model unless a hard rule already
    decided, then the sarcasm contrast, then build the response.
    """
    review = payload.review
    metadata = payload.metadata.model_dump() if payload.metadata else None
    started = time.perf_counter()

    tier1_result = tier1.evaluate(review, metadata) if settings.enable_tier1 else None

    if tier1_result is not None and tier1.short_circuited(tier1_result):
        # Hard rule: the artefacts are never touched for this request.
        rule_latency = int((time.perf_counter() - started) * 1000)
        prediction = predictor.rule_only_prediction(
            review, payload.rating, rule_latency
        )
        prediction.tier1 = tier1.as_response_block(tier1_result)
    else:
        try:
            prediction = predictor.predict_one(review, payload.model, payload.rating)
        except ModelArtifactError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_detail("MODELS_NOT_LOADED", exc.friendly_message()),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=error_detail("INVALID_MODEL", str(exc)),
            ) from exc
        if tier1_result is not None:
            # Soft signals are reported in their own block; the existing
            # ``flags`` list keeps exactly the Phase 3 rules.
            prediction.tier1 = tier1.as_response_block(tier1_result)

    if settings.enable_sarcasm:
        # Runs after the model and never revisits verdict or fake_probability.
        sarcasm_result = sarcasm.analyze(review)
        prediction.sarcasm = sarcasm_result
        prediction.flags = sarcasm.add_flag(prediction.flags, sarcasm_result)

    entry_id = _save_history(review, prediction)
    return _prediction_to_response(review, prediction, entry_id)


# ------------------------------------------------------------------ batch ---
def _decode_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _read_csv_frame(text: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.StringIO(text))
    except pd.errors.EmptyDataError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "CSV_EMPTY", "The uploaded CSV has no content. Include a header row with a 'review' column."
            ),
        ) from exc
    except Exception as exc:  # malformed quotes, mixed delimiters, etc.
        message = str(exc).split("\n")[0]
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "CSV_UNREADABLE",
                f"Could not parse the CSV: {message}. Check quoting and that one comma-separated column is named 'review'.",
            ),
        ) from exc


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(name).strip().lower() for name in frame.columns]
    return frame


def _parse_batch(frame: pd.DataFrame) -> tuple[list[str], list[int | None], list[dict[str, Any]]]:
    if "review" not in frame.columns:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "CSV_MISSING_COLUMN",
                "The CSV must have a 'review' column. Found columns: "
                f"{list(frame.columns)}. Optional: 'rating' (1-5).",
            ),
        )
    if len(frame) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "CSV_NO_ROWS", "The CSV has a header but no data rows to analyze."
            ),
        )
    if len(frame) > settings.max_batch_rows:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=error_detail(
                "CSV_TOO_MANY_ROWS",
                f"The CSV has {len(frame)} rows; the maximum per upload is "
                f"{settings.max_batch_rows}.",
            ),
        )

    reviews: list[str] = []
    blank_rows: list[int] = []
    long_rows: list[int] = []
    for position, value in enumerate(frame["review"].tolist(), start=1):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            blank_rows.append(position)
            text = ""
        else:
            text = str(value).strip()
            if not text:
                blank_rows.append(position)
        if len(text) > settings.max_review_chars:
            long_rows.append(position)
        reviews.append(text)

    shown = ", ".join(str(row) for row in blank_rows[:MAX_ERROR_ROWS_SHOWN])
    if blank_rows:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "CSV_EMPTY_REVIEW",
                f"{len(blank_rows)} row(s) have an empty 'review' value (rows: {shown}...). "
                "Every row needs a review to analyze.",
            ),
        )
    if long_rows:
        shown = ", ".join(str(row) for row in long_rows[:MAX_ERROR_ROWS_SHOWN])
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "CSV_REVIEW_TOO_LONG",
                f"{len(long_rows)} row(s) exceed {settings.max_review_chars} characters (rows: {shown}...).",
            ),
        )

    ratings: list[int | None] = [None] * len(reviews)
    if "rating" in frame.columns:
        bad_rows: list[int] = []
        numeric = pd.to_numeric(frame["rating"], errors="coerce")
        for position, value in enumerate(numeric.tolist(), start=1):
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue  # blank rating stays None (rating is optional)
            try:
                rating_value = int(round(float(value)))
            except (TypeError, ValueError):
                bad_rows.append(position)
                continue
            if not settings.min_rating <= rating_value <= settings.max_rating:
                bad_rows.append(position)
                continue
            ratings[position - 1] = rating_value
        if bad_rows:
            shown = ", ".join(str(row) for row in bad_rows[:MAX_ERROR_ROWS_SHOWN])
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=error_detail(
                    "CSV_INVALID_RATING",
                    f"'rating' must be a whole number between {settings.min_rating} and "
                    f"{settings.max_rating} (bad rows: {shown}...).",
                ),
            )
    return reviews, ratings, _parse_batch_metadata(frame, len(reviews))


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value))


def _parse_batch_metadata(
    frame: pd.DataFrame, expected: int
) -> list[dict[str, Any]]:
    """Per-row Tier-1 context from the optional ``user_id`` / ``posted_at`` columns.

    A CSV that has neither column returns ``[]``, which the endpoint reads as
    "no behaviour signals available" - the batch then behaves exactly like it
    did in Phase 3.
    """
    if "user_id" not in frame.columns and "posted_at" not in frame.columns:
        return []

    user_values = (
        frame["user_id"].tolist() if "user_id" in frame.columns else [None] * expected
    )
    posted_values = (
        frame["posted_at"].tolist() if "posted_at" in frame.columns else [None] * expected
    )

    metas: list[dict[str, Any]] = []
    bad_timestamps: list[int] = []
    for position, (user_value, posted_value) in enumerate(
        zip(user_values, posted_values), start=1
    ):
        meta: dict[str, Any] = {}
        if not _is_blank(user_value):
            user_id = str(user_value).strip()[:128]
            if user_id:
                meta["user_id"] = user_id
        if not _is_blank(posted_value):
            raw = str(posted_value).strip()
            if raw:
                parsed = _parse_iso_timestamp(raw)
                if parsed is None:
                    bad_timestamps.append(position)
                else:
                    meta["posted_at"] = parsed
        metas.append(meta)

    if bad_timestamps:
        shown = ", ".join(str(row) for row in bad_timestamps[:MAX_ERROR_ROWS_SHOWN])
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "CSV_INVALID_POSTED_AT",
                f"'posted_at' must be an ISO-8601 timestamp such as "
                f"2026-01-31T09:15:00Z (bad rows: {shown}...).",
            ),
        )
    return metas


def _parse_iso_timestamp(raw: str) -> datetime | None:
    """ISO-8601 with an optional trailing Z; naive timestamps are read as UTC."""
    candidate = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _summary(predictions) -> dict[str, Any]:
    total = len(predictions)
    fake_count = sum(1 for p in predictions if p.verdict == "fake")
    avg_confidence = (
        sum(p.confidence for p in predictions) / total if total else 0.0
    )
    return {
        "total": total,
        "fake_count": fake_count,
        "fake_percent": round(100.0 * fake_count / total, 4) if total else 0.0,
        "avg_confidence": round(avg_confidence, 4),
    }


BATCH_CSV_COLUMNS = (
    "row",
    "review",
    "rating",
    "verdict",
    "fake_probability",
    "confidence",
    "sentiment_label",
)


def _batch_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(BATCH_CSV_COLUMNS))
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in BATCH_CSV_COLUMNS})
    return buffer.getvalue()


@router.post(
    "/predict/batch",
    summary="Analyze a CSV of reviews (max 5000 rows, 5 MB)",
    response_model=None,
    responses={
        400: {"model": None, "description": "Unreadable or invalid CSV"},
        413: {"model": None, "description": "CSV too large"},
        503: {"model": None, "description": "Models not loaded"},
    },
)
async def predict_batch(
    file: UploadFile = File(
        ...,
        description=(
            "CSV with a required 'review' column. Optional: 'rating' (1-5), "
            "and for Tier-1 'user_id' / 'posted_at' (ISO-8601)."
        ),
    ),
    model: str = Query("best", description="best | nb | svm"),
    output_format: str = Query("json", alias="format", description="json | csv"),
):
    if output_format not in ("json", "csv"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "INVALID_FORMAT", "'format' must be 'json' (default) or 'csv'."
            ),
        )

    raw = await file.read()
    if raw is None or len(raw) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=error_detail("CSV_EMPTY", "The uploaded file is empty."),
        )
    if len(raw) > settings.max_batch_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=error_detail(
                "CSV_TOO_LARGE",
                f"The upload is {len(raw) / 1_048_576:.2f} MB; the limit is "
                f"{settings.max_batch_bytes / 1_048_576:.0f} MB.",
            ),
        )

    text = _decode_csv(raw)
    frame = _normalise_columns(_read_csv_frame(text))
    reviews, ratings, metas = _parse_batch(frame)

    # Tier-1 inside the file: only when the upload actually carries behaviour
    # columns, and always against a tracker scoped to this upload so a CSV can
    # never contaminate the server-side counters.
    tier1_active = settings.enable_tier1 and bool(metas)
    flagged: set[int] = set()
    if tier1_active:
        file_tracker = tier1.Tier1Tracker()
        for index, (review, meta) in enumerate(zip(reviews, metas)):
            result = tier1.evaluate(review, meta, tracker_obj=file_tracker)
            if tier1.short_circuited(result):
                flagged.add(index)

    model_rows = [index for index in range(len(reviews)) if index not in flagged]
    try:
        scored = predictor.predict_many(
            [reviews[index] for index in model_rows],
            model,
            [ratings[index] for index in model_rows],
        )
    except ModelArtifactError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_detail("MODELS_NOT_LOADED", exc.friendly_message()),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=error_detail("INVALID_MODEL", str(exc))
        ) from exc

    predictions: list[Any] = [None] * len(reviews)
    for index, prediction in zip(model_rows, scored):
        predictions[index] = prediction
    for index in flagged:
        # Hard rule in the file: same vectorised path, minus the model.
        predictions[index] = predictor.rule_only_prediction(
            reviews[index], ratings[index]
        )

    rows = [
        BatchRow(
            row=index + 1,
            review=review,
            rating=rating,
            verdict=prediction.verdict,
            fake_probability=prediction.fake_probability,
            confidence=prediction.confidence,
            sentiment_label=prediction.sentiment["label"],
        ).model_dump()
        for index, (review, rating, prediction) in enumerate(
            zip(reviews, ratings, predictions)
        )
    ]

    if output_format == "csv":
        from fastapi.responses import Response

        return Response(
            content=_batch_csv(rows),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="truthlens-batch-results.csv"'
            },
        )

    summary = _summary(predictions)
    if tier1_active:
        # New optional key: only a CSV with user_id / posted_at changes shape.
        summary["tier1_flagged"] = len(flagged)
        return {"rows": rows, "summary": summary}
    return BatchResponse(rows=rows, summary=BatchSummary(**summary))


def validate_predict_payload(payload: dict) -> PredictRequest:
    """Helper used by tests/rate-limits: build a typed request or raise 422."""
    try:
        return PredictRequest(**payload)
    except ValidationError as exc:  # pragma: no cover - FastAPI does this itself
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_detail("VALIDATION_ERROR", str(exc)),
        ) from exc
