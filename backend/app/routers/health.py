"""Service status: GET /api/health."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.config import APP_VERSION
from app.schemas import HealthResponse
from app.services.predictor import predictor

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service status")
def health() -> dict[str, Any]:
    loaded = predictor.is_loaded
    return HealthResponse(
        status="ok" if loaded else "degraded",
        models_loaded=loaded,
        version=APP_VERSION,
    ).model_dump()
