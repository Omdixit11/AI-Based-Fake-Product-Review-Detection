"""FastAPI application: CORS, startup (models loaded once), error envelope, logging.

Contract notes:
* every error is ``{"error": {"code": ..., "message": ...}}`` with a correct
  HTTP status; stack traces are never returned to the client;
* the trained artifacts are loaded exactly once, in the lifespan handler.
"""
from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import APP_NAME, APP_VERSION, settings
from app.db.database import database
from app.routers import health, history, models, predict
from app.services.predictor import ModelArtifactError, predictor

logger = logging.getLogger("truthlens.api")

# One structured line per request: method path status latency_ms ip
_REQUEST_LINE = (
    'request method={method} path={path} status={status} latency_ms={latency} ip={ip}'
)


def configure_logging() -> None:
    root = logging.getLogger()
    if any(getattr(h, "_truthlens_api", False) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler._truthlens_api = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class _LimitBucket:
    """Tiny in-memory sliding-window counter per IP (no extra dependency)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def add_and_check(self, key: str, limit_per_minute: int) -> bool:
        """Return True when the caller is within the limit."""
        if limit_per_minute <= 0:
            return True
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= limit_per_minute:
            return False
        window.append(now)
        return True

    def clear(self) -> None:
        self._hits.clear()


_limiter = _LimitBucket()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def error_json(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    database.create_tables()
    # Fail fast with a message naming the missing file and how to create it.
    predictor.load()
    logger.info(
        "TruthLens API ready: best_model=%s feature_set=%s artifacts=%s",
        predictor.best_model,
        predictor.active_feature_set,
        predictor.models_dir,
    )
    yield
    logger.info("TruthLens API shutting down")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Fake vs genuine product review analyzer (Phase 3 backend).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATUS_CODES = {
    "validation_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "bad_request": status.HTTP_400_BAD_REQUEST,
    "not_found": status.HTTP_404_NOT_FOUND,
    "method_not_allowed": status.HTTP_405_METHOD_NOT_ALLOWED,
    "payload_too_large": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    "too_many_requests": status.HTTP_429_TOO_MANY_REQUESTS,
    "unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "internal": status.HTTP_500_INTERNAL_SERVER_ERROR,
}

_CODE_FOR_STATUS = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "MODELS_NOT_LOADED",
}


@app.middleware("http")
async def request_observability(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # pragma: no cover - handled by the exception handler
        latency = int((time.perf_counter() - start) * 1000)
        logger.error(
            _REQUEST_LINE.format(
                method=request.method,
                path=request.url.path,
                status=500,
                latency=latency,
                ip=_client_ip(request),
            )
        )
        raise
    latency = int((time.perf_counter() - start) * 1000)
    line = _REQUEST_LINE.format(
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency=latency,
        ip=_client_ip(request),
    )
    (logger.info if response.status_code < 500 else logger.error)(line)
    response.headers["X-Process-Time-Ms"] = str(latency)
    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api") and request.method != "OPTIONS":
        limit = settings.rate_limit_per_minute
        if not _limiter.add_and_check(_client_ip(request), limit):
            return error_json(
                _STATUS_CODES["too_many_requests"],
                "RATE_LIMITED",
                f"Too many requests from this IP. Limit is {limit} requests/minute.",
            )
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        error = detail["error"]
        if isinstance(error, dict) and "code" in error and "message" in error:
            return error_json(exc.status_code, str(error["code"]), str(error["message"]))
    message = detail if isinstance(detail, str) else "Request could not be processed."
    code = _CODE_FOR_STATUS.get(exc.status_code, "HTTP_ERROR")
    return error_json(exc.status_code, code, message)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    parts: list[str] = []
    for issue in exc.errors():
        loc = ".".join(str(p) for p in issue.get("loc", []) if p not in ("body",))
        raw_message = str(issue.get("msg", "invalid value"))
        # Pydantic wraps our ValueError text in quotes sometimes; keep it tidy.
        raw_message = re.sub(r'^Value error,\s*', "", raw_message).strip().strip('"')
        parts.append(f"{loc}: {raw_message}" if loc else raw_message)
    message = "; ".join(parts) or "Invalid request payload."
    return error_json(_STATUS_CODES["validation_error"], "VALIDATION_ERROR", message)


@app.exception_handler(ModelArtifactError)
async def artifact_exception_handler(request: Request, exc: ModelArtifactError):
    return error_json(
        _STATUS_CODES["unavailable"], "MODELS_NOT_LOADED", exc.friendly_message()
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Logged with the traceback, never shown to the caller.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_json(
        _STATUS_CODES["internal"],
        "INTERNAL_ERROR",
        "The server failed to analyze this request. Please try again.",
    )


app.include_router(predict.router)
app.include_router(models.router)
app.include_router(history.router)
app.include_router(health.router)


def reset_rate_limiter() -> None:
    """Test helper: forget recorded request counts."""
    _limiter.clear()


def get_app_state() -> dict[str, Any]:
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "cors_origins": list(settings.cors_origins),
        "models_loaded": predictor.is_loaded,
    }
