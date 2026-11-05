"""POST /api/explain: on-demand token explanations, separate from /api/predict.

Phase 3.5 feature 3. Kept on its own endpoint (and its own router) so the
prediction hot path stays exactly as fast as it was in Phase 3.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.schemas import ExplainRequest, ExplainResponse, error_detail
from app.services import explain_shap
from app.services.predictor import ModelArtifactError, predictor

router = APIRouter(prefix="/api", tags=["explain"])


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain one review with SHAP (SVM) or log-probabilities (NB)",
    responses={
        422: {"model": None, "description": "Validation error"},
        400: {"model": None, "description": "Invalid model choice"},
        503: {"model": None, "description": "Models not loaded"},
    },
)
def explain(payload: ExplainRequest) -> dict[str, Any]:
    """Top 10 contributing tokens for one review.

    ``method`` tells the truth about what produced them: ``shap-linear`` when
    the optional ``shap`` package ran (or when its identical value was computed
    directly because the library is present but raised), ``linear-coefficients``
    when ``shap`` is not installed or ``ENABLE_SHAP=false``, and
    ``naive-bayes-logprob`` for Naive Bayes, which has no SHAP here.
    """
    try:
        return explain_shap.explain_review(payload.review, payload.model, predictor)
    except ModelArtifactError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_detail("MODELS_NOT_LOADED", exc.friendly_message()),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=error_detail("INVALID_MODEL", str(exc))
        ) from exc
