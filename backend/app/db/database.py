"""SQLAlchemy engine/session helpers for the SQLite history store.

The engine is created lazily from ``settings.database_url`` so that tests can
point the API at a temporary SQLite file (never a committed ``.db``).
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by the ORM models in ``app.db.models``."""


class _Database:
    """Holds the engine and session factory, rebuilt when the URL changes."""

    def __init__(self) -> None:
        self._url: str | None = None
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def _build(self, url: str) -> None:
        kwargs: dict = {"future": True}
        if url.startswith("sqlite"):
            # FastAPI runs path operations in a worker thread; SQLite needs
            # check_same_thread disabled plus a shared cache for that to work.
            kwargs["connect_args"] = {"check_same_thread": False}
        self._engine = create_engine(url, **kwargs)
        self._session_factory = sessionmaker(
            bind=self._engine, future=True, expire_on_commit=False
        )
        self._url = url

    @property
    def engine(self) -> Engine:
        if self._engine is None or self._url != settings.database_url:
            self._build(settings.database_url)
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        if self._session_factory is None or self._url != settings.database_url:
            self._build(settings.database_url)
        return self._session_factory

    def create_tables(self) -> None:
        from app.db import models  # noqa: F401 - registers the ORM classes

        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        from app.db import models  # noqa: F401

        Base.metadata.drop_all(self.engine)

    def reset(self) -> None:
        """Dispose the engine so the next use re-reads ``settings``."""
        if self._engine is not None:
            self._engine.dispose()
        self._url = None
        self._engine = None
        self._session_factory = None


database = _Database()


def get_session() -> Session:
    return database.session_factory()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope used by the services and routers."""
    session = database.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session."""
    with session_scope() as session:
        yield session
