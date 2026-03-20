"""Fábrica de engine SQLite e sessões SQLAlchemy para histórico de execuções."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db import models as _db_models  # noqa: F401 — registra tabelas
from app.db.models import Base

log = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


# Libera singleton (testes ou troca de `DATABASE_URL`).
def reset_engine() -> None:
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None


# Cria engine singleton, garante pasta do SQLite e `create_all` nas tabelas declaradas.
def get_engine():
    global _engine
    if _engine is None:
        url = settings.DATABASE_URL
        if url.startswith("sqlite:///"):
            db_path = Path(url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, echo=False, future=True)
        Base.metadata.create_all(bind=_engine)
        log.debug("Database ready: %s", url.split("@")[-1] if "@" in url else url)
    return _engine


# Retorna `sessionmaker` ligado ao `get_engine()` (lazy singleton).
def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), class_=Session, autoflush=False, autocommit=False)
    return _SessionLocal


# Context manager for DB session.
def session_scope():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
