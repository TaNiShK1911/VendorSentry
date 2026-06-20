"""
Database session factory and FastAPI dependency.

This module re-exports from core.database to maintain backward compatibility.
The single source of truth is app.core.database.
"""
from app.core.database import engine, SessionLocal, get_db  # noqa: F401
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for non-FastAPI use (scripts, Celery tasks)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
