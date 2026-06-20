# VendorSentry — AI-Powered Third-Party & Vendor Risk Intelligence

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Track:** Third-Party Risk & Governance  
> **Approach:** Option A — AI-Powered Vendor Intelligence  
> **Difficulty:** Advanced

VendorSentry is a production-ready implementation of **Option A — AI-Powered Vendor Intelligence**, featuring multi-source data ingestion (contracts, security assessments, audit reports, certifications, breach databases, and public records), LLM-powered extraction and narrative generation, deterministic risk scoring, and continuous monitoring with Red/Yellow/Green portfolio visualization.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd VendorSentry

# Start the full stack
make dev

# The API will be available at:
# - API: http://localhost:8000
# - Interactive Docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

That's it! The `make dev` command:
1. Builds all Docker images
2. Starts PostgreSQL, Redis, API, Celery Worker, and Celery Beat
3. Seeds the database with sample vendor data
4. Runs initial risk scoring

### Alternative: Manual Setup

```bash
# Build images
docker compose build

# Start services
docker compose up -d

# Seed database
docker compose exec api python scripts/seed.py

# View logs
docker compose logs -f
```

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| [`PRD.md`](./PRD.md) | Product requirements, problem statement, success metrics |
| [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) | Technical architecture, data pipeline, phased build plan |
| [`BACKEND_INTEGRATION.md`](./BACKEND_INTEGRATION.md) | Complete API contract for frontend integration |
| [`CONTRIBUTION.md`](./CONTRIBUTION.md) | 2-developer backend split (Dev A vs Dev B responsibilities) |
| [`AGENT.md`](./AGENT.md) | Conventions for AI coding agents working in this repo |
| [`NOVELTY.md`](./NOVELTY.md) | What differentiates VendorSentry from other implementations |
| [`backend/README.md`](./backend/README.md) | Backend-specific documentation and architecture |

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (React)                          │
│              [Portfolio Dashboard + Drill-Down]               │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST API (JSON)
┌────────────────────────▼─────────────────────────────────────┐
│                   FastAPI Backend                             │
│  /vendors  /scoring  /alerts  /extraction  /reports          │
└──┬─────────┬──────────┬──────────┬──────────────────────────┘
   │         │          │          │
   │    ┌────▼────┐ ┌───▼────┐ ┌──▼──────────────┐
   │    │ Redis   │ │Postgres│ │ LLM API          │
   │    │ (Queue) │ │  (Data)│ │ (Extraction)     │
   │    └────▲────┘ └────────┘ └──────────────────┘
   │         │
┌──▼─────────┴──────────────────────────────────┐
│         Celery Workers + Beat                  │
│  • Cert Expiry Sweep                          │
│  • Contract Expiry Sweep                      │
│  • Breach DB Polling                          │
│  • Assessment Overdue Check                   │
│  • Risk Rescoring                             │
└────────────────────────────────────────────────┘
```

### Tech Stack

- **Backend:** Python 3.11, FastAPI, PostgreSQL, SQLAlchemy, Alembic
- **Task Queue:** Celery + Redis (background monitoring sweeps)
- **AI Layer:** Anthropic Claude API (for extraction & narrative generation)
- **Data Processing:** Pandas (CSV ingestion, normalization)
- **Testing:** pytest with full endpoint coverage
- **Infrastructure:** Docker Compose for local development

## ✨ Features Implemented

### ✅ Dev B (Current Implementation)

**API Layer** (Complete per `BACKEND_INTEGRATION.md`)
- ✅ Vendor CRUD endpoints with filtering, sorting, pagination
- ✅ Scoring endpoints (get score, rescore, portfolio distribution, trends)
- ✅ Alert endpoints (list, acknowledge, resolve, summary)
- ✅ Extraction endpoints (document upload, job polling, evidence trail)
- ✅ Reporting endpoints (vendor & portfolio reports, Markdown/PDF)
- ✅ Authentication (JWT-based with role support)

**Monitoring & Alerts**
- ✅ Celery beat scheduled sweeps
- ✅ Certification expiry monitoring (60/30/7 day alerts)
- ✅ Contract expiry monitoring (60 day alert)
- ✅ Assessment overdue detection (>12 months)
- ✅ Mock breach DB polling
- ✅ Alert deduplication (hash-based dedup keys)
- ✅ Score tier change alerts

**Infrastructure**
- ✅ Docker Compose setup (api, postgres, redis, worker, beat)
- ✅ Alembic migrations
- ✅ Database models (Vendor, VendorScore, Alert, ExtractionJob, EvidenceSignal)
- ✅ Pydantic schemas (shared contract layer)
- ✅ CSV seed script with partial-failure tolerance
- ✅ pytest test suite

**Reporting**
- ✅ Vendor risk reports (Markdown format)
- ✅ Portfolio reports
- ✅ GDPR/NIST/SOX compliance framing
- ✅ PDF generation stub (ready for reportlab)

### 🔄 Dev A (Stub Implementations Provided)

**Ready for Integration:**
- ⏳ Real scoring engine (`services/scoring/engine.py`)
- ⏳ LLM extraction service (`services/extraction/extractor.py`)
- ⏳ Narrative generation
- ⏳ Evaluation harness (`scripts/evaluate.py`)

The stub implementations allow all endpoints to work immediately. When Dev A delivers real implementations, they slot in with **zero API changes**.

## 📊 API Endpoints

### Vendors
- `GET /api/v1/vendors` - List/filter vendors (portfolio grid)
- `GET /api/v1/vendors/{id}` - Get vendor detail
- `POST /api/v1/vendors` - Create vendor
- `PATCH /api/v1/vendors/{id}` - Update vendor (triggers rescore)
- `DELETE /api/v1/vendors/{id}` - Soft delete vendor
- `POST /api/v1/vendors/import` - CSV bulk import
- `GET /api/v1/vendors/export.csv` - CSV export

### Scoring
- `GET /api/v1/vendors/{id}/score` - Get full score breakdown
- `POST /api/v1/vendors/{id}/rescore` - Force immediate recompute
- `GET /api/v1/portfolio/score-distribution` - Red/Yellow/Green counts
- `GET /api/v1/portfolio/score-trend` - Historical trend data

### Alerts
- `GET /api/v1/alerts` - List/filter alerts
- `POST /api/v1/alerts/{id}/acknowledge` - Acknowledge alert
- `POST /api/v1/alerts/{id}/resolve` - Resolve alert
- `GET /api/v1/alerts/summary` - Badge counts (critical/high/total)

### Extraction & Evidence
- `POST /api/v1/vendors/{id}/extract` - Upload document for extraction
- `GET /api/v1/extraction-jobs/{id}` - Poll extraction job status
- `GET /api/v1/vendors/{id}/evidence` - Get evidence signal trail

### Reports
- `GET /api/v1/vendors/{id}/report` - Generate vendor audit report
- `GET /api/v1/portfolio/report` - Generate portfolio report

### Authentication
- `POST /api/v1/auth/login` - Login (returns JWT token)

**Interactive API documentation:** http://localhost:8000/docs

## 🧪 Testing

```bash
# Run all tests
make test

# Or manually
docker compose exec api pytest -v

# Run specific test file
docker compose exec api pytest app/tests/test_vendors.py -v

# With coverage
docker compose exec api pytest --cov=app --cov-report=html
```

## 🗂️ Project Structure

```
VendorSentry/
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI route handlers
│   │   │   ├── vendors.py
│   │   │   ├── scoring.py
│   │   │   ├── alerts.py
│   │   │   ├── extraction.py
│   │   │   ├── reports.py
│   │   │   └── auth.py
│   │   ├── core/                # Configuration & infrastructure
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   └── celery_app.py
│   │   ├── models/              # SQLAlchemy models (shared)
│   │   ├── schemas/             # Pydantic schemas (shared)
│   │   ├── services/
│   │   │   ├── scoring/         # Risk scoring engine (stub)
│   │   │   ├── extraction/      # LLM extraction (stub)
│   │   │   ├── monitoring/      # Celery sweeps
│   │   │   ├── alerts/          # Alert generation & dedup
│   │   │   └── reporting/       # Report generation
│   │   ├── tests/               # pytest test suite
│   │   └── main.py              # FastAPI app
│   ├── scripts/
│   │   └── seed.py              # CSV ingestion
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── sample_data/
│   ├── vendor_registry.csv      # Seed data (5 vendors)
│   └── vendor_labels.csv        # Ground truth (evaluation)
├── docker-compose.yml
├── Makefile
└── [documentation files]
```

## 🔧 Development

### Common Commands

```bash
make help       # Show all available commands
make build      # Build Docker images
make up         # Start services
make down       # Stop services
make restart    # Restart services
make logs       # View logs
make seed       # Seed database
make test       # Run tests
make shell      # Open shell in API container
make clean      # Remove all containers and volumes
```

### Making Changes

1. **Edit code** - Files in `backend/app/` are mounted as volumes, changes reflect immediately
2. **Database changes** - Create Alembic migration: `docker compose exec api alembic revision -m "description"`
3. **Dependencies** - Add to `requirements.txt`, then `make build && make restart`
4. **Tests** - Add tests to `backend/app/tests/`, run with `make test`

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql://vendorsentry:vendorsentry@postgres:5432/vendorsentry
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-change-in-production
ANTHROPIC_API_KEY=your-api-key  # For Dev A's extraction service
```

## 📋 Implementation Status

### Completed (Dev B)
- [x] Directory structure and project scaffolding
- [x] Database models and Pydantic schemas
- [x] FastAPI app skeleton with CORS and error handling
- [x] All API endpoints per BACKEND_INTEGRATION.md
- [x] Celery monitoring sweeps (cert, contract, breach, assessment)
- [x] Alert system with deduplication
- [x] Report generation (Markdown)
- [x] CSV seed script with error tolerance
- [x] Docker Compose with all services
- [x] pytest test suite
- [x] Documentation

### Ready for Dev A Integration
- [ ] Real scoring engine implementation
- [ ] LLM extraction service (Claude API integration)
- [ ] Narrative generation with grounding
- [ ] Evaluation harness (precision/recall vs ground truth)

### Future Enhancements (Post-Hackathon)
- [ ] Real breach intelligence feeds
- [ ] ITSM integrations (Jira, ServiceNow)
- [ ] Multi-tenant RBAC
- [ ] WebSocket support for live updates
- [ ] PDF generation with reportlab
- [ ] Enrichment adapters (financial health, regulatory data)

## 🤝 Contributing

See [`CONTRIBUTION.md`](./CONTRIBUTION.md) for the 2-developer backend split.

**Dev B (this implementation)** owns:
- API layer, monitoring, alerts, reporting
- Infrastructure (Docker, Celery, migrations)

**Dev A** owns:
- Scoring logic, LLM extraction, evaluation

**Shared:**
- Database models, Pydantic schemas, function signatures

## 📝 License

MIT

## 🙏 Acknowledgments

Built following the implementation plan in `IMPLEMENTATION_PLAN.md` and API contract in `BACKEND_INTEGRATION.md`.

---

**Status:** ✅ Dev B implementation complete and ready for Dev A integration

For questions or issues, refer to [`AGENT.md`](./AGENT.md) for development conventions.
