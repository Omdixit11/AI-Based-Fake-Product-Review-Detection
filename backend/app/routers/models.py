"""Model catalog endpoints: GET /api/models and GET /api/models/metrics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.config import METRICS_PATH, MODEL_NAMES
from app.schemas import ModelInfo, error_detail
from app.services.predictor import predictor

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=ModelInfo, summary="Available models and the default")
def list_models() -> dict[str, Any]:
    predictor.load()
    return ModelInfo(
        models=list(MODEL_NAMES),
        default="best",
        best_model=predictor.best_model,
        active_feature_set=predictor.active_feature_set,
    ).model_dump()


@router.get(
    "/metrics",
    summary="Training metrics (metrics.json, returned as is)",
    response_model=None,
)
def get_metrics() -> Any:
    """Serve backend/models/metrics.json verbatim - no reshaping, no invented keys."""
    path = Path(METRICS_PATH)
    if not path.exists():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_detail(
                "METRICS_NOT_FOUND",
                f"{path} is missing. Phase 2 writes it with  cd backend && python -m ml.run_pipeline.",
            ),
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail("METRICS_UNREADABLE", f"{path.name} is not valid JSON: {exc}"),
        ) from exc
