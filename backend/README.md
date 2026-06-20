# VendorSentry Backend

Backend implementation for VendorSentry - AI-Powered Third-Party & Vendor Risk Intelligence.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker Compose

```bash
# Copy environment file
cp .env.example .env

# Start all services (api, postgres, redis, worker, beat)
docker compose up --build

# The API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Seeding the Database

```bash
# Run the seed script (inside the container or locally)
docker compose exec api python scripts/seed.py

# Or locally:
python backend/scripts/seed.py
```

### Running Tests

```bash
# Inside container
docker compose exec api pytest

# Or locally
cd backend
pytest
```

## Architecture

This is **Dev B's implementation** per `CONTRIBUTION.md`:

### Responsibilities
- FastAPI application skeleton and core infrastructure
- All API endpoints (`/vendors`, `/scoring`, `/alerts`, `/extraction`, `/reports`, `/auth`)
- Celery monitoring sweeps (cert expiry, contract expiry, breach polling, assessment overdue)
- Alert system with deduplication
- Reporting (Markdown/PDF generation)
- Docker Compose setup
- Database migrations (Alembic)

### Shared with Dev A
- Database models (`app/models/`)
- Pydantic schemas (`app/schemas/`)
- Scoring function signature

### Dev A's Domain (Stub implementations provided)
- Real scoring engine logic (`app/services/scoring/engine.py`)
- LLM extraction service (`app/services/extraction/extractor.py`)
- Narrative generation
- Evaluation harness

## API Documentation

Interactive API docs available at `/docs` when running.

Full API contract documented in `../BACKEND_INTEGRATION.md`.

Key endpoints:
- `GET /api/v1/vendors` - List/filter vendors
- `GET /api/v1/vendors/{id}/score` - Get risk score breakdown
- `GET /api/v1/alerts` - List alerts
- `GET /api/v1/portfolio/score-distribution` - Portfolio Red/Yellow/Green view
- `POST /api/v1/vendors/{id}/extract` - Upload document for extraction
- `GET /api/v1/vendors/{id}/report` - Generate audit report

## Project Structure

```
backend/
├── app/
│   ├── api/              # FastAPI route handlers
│   ├── core/             # Config, database, security, Celery
│   ├── models/           # SQLAlchemy models (shared with Dev A)
│   ├── schemas/          # Pydantic schemas (shared with Dev A)
│   ├── services/
│   │   ├── alerts/       # Alert generation & dedup
│   │   ├── monitoring/   # Celery sweeps
│   │   ├── reporting/    # Report generation
│   │   ├── scoring/      # Stub scoring engine (Dev A replaces)
│   │   └── extraction/   # Stub LLM service (Dev A replaces)
│   ├── tests/            # Pytest tests
│   └── main.py           # FastAPI app
├── scripts/
│   └── seed.py           # CSV ingestion
├── alembic/              # Database migrations
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Development

### Local Setup (without Docker)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database URL, Redis URL, etc.

# Run migrations
alembic upgrade head

# Run the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In separate terminals, run:
# Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Celery beat (scheduler)
celery -A app.core.celery_app beat --loglevel=info
```

### Running Tests

```bash
pytest                    # All tests
pytest -v                 # Verbose
pytest -k test_vendors    # Specific test file
```

## Key Features Implemented

✅ **API Layer** - All endpoints per BACKEND_INTEGRATION.md
✅ **Monitoring Sweeps** - Cert/contract expiry, breach polling, assessment overdue
✅ **Alert System** - Generation, deduplication, acknowledge/resolve
✅ **Reporting** - Vendor and portfolio report generation
✅ **Authentication** - Basic JWT auth with role support
✅ **Docker Compose** - Full stack orchestration
✅ **Database Models** - Complete SQLAlchemy schema
✅ **Tests** - Pytest coverage for core endpoints

## Integration with Dev A

Dev A implements:
- Real scoring engine in `app/services/scoring/engine.py`
- LLM extraction in `app/services/extraction/`
- Evaluation harness in `scripts/evaluate.py`

The stub implementations provided allow Dev B's endpoints to work immediately.
When Dev A delivers the real implementations, they slot in with zero API changes.

## Notes

- Per AGENT.md, ground truth (`vendor_labels.csv`) is evaluation-only
- Alert dedup prevents duplicate firing (hash-based dedup keys)
- CSV ingestion is partial-failure tolerant (malformed rows logged, batch continues)
- All Celery tasks are idempotent

## Sync Points (per CONTRIBUTION.md)

- ✅ Hour 4: DB models frozen, scoring stub signature agreed
- ⏳ Hour 14: Dev A's real scoring engine replaces stub
- ⏳ Hour 24: Integration test (seed → score → alert → report)
