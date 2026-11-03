"""History endpoints: list with filters, delete one entry, clear all."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select

from app.config import settings
from app.db.database import session_scope
from app.db.models import History
from app.schemas import HistoryEntry, HistoryListResponse, error_detail

router = APIRouter(prefix="/api/history", tags=["history"])

VALID_VERDICTS = ("fake", "genuine")

LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    """Escape LIKE wildcards so a search string is matched literally."""
    return (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE + LIKE_ESCAPE)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )


@router.get("", response_model=HistoryListResponse, summary="List past analyses")
def list_history(
    search: str | None = Query(None, description="Case-insensitive text search"),
    verdict: str | None = Query(None, description="fake | genuine"),
    limit: int | None = Query(None, ge=1, description="Page size"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
) -> dict[str, Any]:
    if verdict is not None and verdict.strip():
        verdict_value = verdict.strip().lower()
        if verdict_value not in VALID_VERDICTS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=error_detail(
                    "INVALID_VERDICT",
                    f"'verdict' must be one of {list(VALID_VERDICTS)}, got {verdict!r}.",
                ),
            )
    else:
        verdict_value = None

    page_size = limit if limit is not None else settings.history_default_limit
    page_size = min(int(page_size), settings.history_max_limit)

    filters = []
    if verdict_value:
        filters.append(History.verdict == verdict_value)
    term = (search or "").strip()
    if term:
        filters.append(
            History.review_text.ilike(f"%{_escape_like(term)}%", escape=LIKE_ESCAPE)
        )

    with session_scope() as session:
        count_statement = select(func.count(History.id))
        for condition in filters:
            count_statement = count_statement.where(condition)
        total = int(session.execute(count_statement).scalar_one())

        statement = select(History).order_by(History.created_at.desc(), History.id.desc())
        for condition in filters:
            statement = statement.where(condition)
        statement = statement.limit(page_size).offset(offset)
        entries = [
            HistoryEntry(**row.to_dict()).model_dump()
            for row in session.execute(statement).scalars().all()
        ]

    # ``entries`` is what the committed frontend reads; ``items`` is the name used
    # by the Phase 3 spec. Both carry the same array (see docs/LLD.md, which does
    # not pin this key).
    return {"total": total, "entries": entries, "items": entries}


@router.delete("/{entry_id}", summary="Delete one history entry")
def delete_entry(entry_id: int) -> dict[str, Any]:
    with session_scope() as session:
        row = session.get(History, int(entry_id))
        if row is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=error_detail(
                    "HISTORY_NOT_FOUND", f"No history entry with id {entry_id}."
                ),
            )
        session.delete(row)
        session.flush()
    return {"deleted": 1, "id": int(entry_id)}


@router.delete("", summary="Clear the whole history")
def clear_history() -> dict[str, Any]:
    with session_scope() as session:
        total = int(session.execute(select(func.count(History.id))).scalar_one())
        if total:
            session.execute(delete(History))
            session.flush()
    return {"deleted": total}
