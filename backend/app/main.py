"""
VendorSentry FastAPI application factory.

Dev A provides the app skeleton here; Dev B fills in the routers.
The app itself is wired, CORS is set, and the health endpoint is live
so Dev B can test the container from hour 1.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
)

app = FastAPI(
    title="VendorSentry API",
    description=(
        "AI-powered third-party vendor risk intelligence. "
        "See BACKEND_INTEGRATION.md for the full API contract."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — allow the frontend dev server during the hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten before any real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup: auto-create tables for SQLite dev mode ─────────────────────────
@app.on_event("startup")
def on_startup():
    """Create all tables on startup (SQLite dev mode — no Alembic needed)."""
    from app.models.base import Base
    from app.core.database import engine
    # Import all models so Base.metadata knows about them
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logging.getLogger("vendorsentry").info("Database tables created/verified.")


# ── Health check (available immediately for Dev B to test) ──────────────────
@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "service": "vendorsentry-api"}


# ── API routers ─────────────────────────────────────────────────────────────
from app.api import vendors, scoring, alerts, reports, extraction, auth, evaluation

app.include_router(vendors.router,    prefix="/api/v1", tags=["vendors"])
app.include_router(scoring.router,    prefix="/api/v1", tags=["scoring"])
app.include_router(alerts.router,     prefix="/api/v1", tags=["alerts"])
app.include_router(reports.router,    prefix="/api/v1", tags=["reports"])
app.include_router(extraction.router, prefix="/api/v1", tags=["extraction"])
app.include_router(auth.router,       prefix="/api/v1/auth", tags=["auth"])
app.include_router(evaluation.router, prefix="/api/v1", tags=["evaluation"])
