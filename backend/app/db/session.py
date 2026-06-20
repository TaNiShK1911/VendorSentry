"""
Database session factory and FastAPI dependency.

Usage in FastAPI route:
    def my_endpoint(db: Session = Depends(get_db)):
        ...

Usage in scripts (sync):
    with SessionLocal() as db:
        ...
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # Reconnects if connection drops
    pool_size=10,
    max_overflow=20,
    echo=(settings.environment == "development"),  # SQL logging in dev only
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # Avoids lazy-loading errors after commit
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a DB session per request."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
