"""ORM model for the ``history`` table.

Column names come straight from docs/LLD.md section 4; the frontend reads
``flags_json`` and ``tokens_json`` as raw JSON strings, so they stay strings
here and are never re-shaped by the API.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class History(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    fake_probability: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(8), nullable=False)
    compound: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tokens_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    __table_args__ = (Index("ix_history_verdict_created", "verdict", "created_at"),)

    def iso_created_at(self) -> str:
        """ISO-8601 timestamp; naive SQLite datetimes are stored as UTC."""
        moment = self.created_at
        if moment is None:
            return ""
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.isoformat()

    def to_dict(self) -> dict:
        """Shape used by GET /api/history (matches the frontend HistoryEntry)."""
        return {
            "id": self.id,
            "review_text": self.review_text,
            "verdict": self.verdict,
            "fake_probability": self.fake_probability,
            "model_used": self.model_used,
            "compound": self.compound,
            "flags_json": self.flags_json,
            "tokens_json": self.tokens_json,
            "created_at": self.iso_created_at(),
        }
