# VendorSentry — AI-Powered Third-Party & Vendor Risk Intelligence

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5-purple.svg)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Track:** Third-Party Risk & Governance  
> **Approach:** Option A — AI-Powered Vendor Intelligence  
> **Difficulty:** Advanced

VendorSentry is a production-ready implementation of **Option A — AI-Powered Vendor Intelligence**, featuring multi-source data ingestion (contracts, security assessments, audit reports, certifications, breach databases, and public records), LLM-powered extraction and narrative generation, deterministic risk scoring, and continuous monitoring with Red/Yellow/Green portfolio visualization.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### Running with Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd VendorSentry

# Start the full stack
docker compose up --build -d

# Seed the database with sample data
docker compose exec api python scripts/seed.py

# The application will be available at:
# - Frontend: http://localhost:5173
# - API: http://localhost:8000
# - Interactive API Docs: http://localhost:8000/docs
```

### Manual Local Setup

**1. Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables (copy .env.example to .env)
# Start PostgreSQL and Redis locally, update .env with credentials

alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

**2. Frontend Setup**
```bash
cd app
npm install
npm run dev
```

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| [`PRD.md`](./PRD.md) | Product requirements, problem statement, success metrics |
| [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) | Technical architecture, data pipeline, phased build plan |
| [`BACKEND_INTEGRATION.md`](./BACKEND_INTEGRATION.md) | Complete API contract for frontend integration |
| [`CONTRIBUTION.md`](./CONTRIBUTION.md) | 2-developer backend split (Dev A vs Dev B responsibilities) |
| [`DESIGN.md`](./DESIGN.md) | Brand and style guidelines for the UI |
| [`NOVELTY.md`](./NOVELTY.md) | What differentiates VendorSentry from other implementations |
| [`backend/README.md`](./backend/README.md) | Backend-specific documentation and architecture |

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                  │
│              [Portfolio Dashboard + Copilot Panel]           │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST API (JSON)
┌────────────────────────▼─────────────────────────────────────┐
│                   FastAPI Backend                            │
│  /vendors  /scoring  /alerts  /extraction  /copilot          │
└──┬─────────┬──────────┬──────────┬──────────────────────────┘
   │         │          │          │
   │    ┌────▼────┐ ┌───▼────┐ ┌──▼──────────────┐
   │    │ Redis   │ │Postgres│ │ LLM API         │
   │    │ (Queue) │ │  (Data)│ │ (Groq/Llama-3)  │
   │    └────▲────┘ └────────┘ └──────────────────┘
   │         │
┌──▼─────────┴──────────────────────────────────┐
│         Celery Workers + Beat                 │
│  • Cert Expiry Sweep                          │
│  • Contract Expiry Sweep                      │
│  • Breach DB Polling                          │
│  • Risk Rescoring                             │
└────────────────────────────────────────────────┘
```

## ✨ Features

### 🛡️ Core Vendor Intelligence
- **Vendor Registry**: Comprehensive tracking of vendor profiles, compliance posture, and data access scopes.
- **Continuous Monitoring**: Automated sweeps for expiring certifications, contract renewals, and overdue assessments.
- **Deterministic Risk Scoring**: Formula-based risk score combining breach history, data access scope, compliance maturity, and financial stability.
- **Alerts & Deduplication**: Smart alert routing for critical security events without alert fatigue.

### 🤖 AI-Powered Copilot
- **Live Data Grounding**: Conversational interface backed by the live Postgres database — no hallucinations.
- **Tool-Use Architecture**: Uses state-of-the-art LLMs (Llama 3.1/3.3 via Groq) with function calling to execute dynamic queries against the API.
- **Provenance Tracking**: Every answer cites the exact database queries and endpoints used.
- **Follow-up Suggestions**: Context-aware recommendations for deeper investigation.

### 📊 Portfolio Dashboard
- **Risk Heatmap**: Red/Yellow/Green visualization of the entire vendor ecosystem.
- **Drill-down Views**: Detailed vendor pages with score breakdowns and historical trends.
- **Export & Reporting**: Generate Markdown-based audit reports for compliance teams.

## 🗂️ Project Structure

```
VendorSentry/
├── app/                      # React Frontend
│   ├── src/
│   │   ├── api/              # API client layer
│   │   ├── components/       # Reusable UI components
│   │   ├── hooks/            # Custom React hooks (e.g., useCopilot)
│   │   ├── layouts/          # Page layouts
│   │   └── pages/            # View components
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/              # Route handlers
│   │   ├── core/             # Config & infrastructure
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic (scoring, copilot, monitoring)
│   │   └── tests/            # pytest suite
│   ├── alembic/              # Database migrations
│   ├── scripts/              # DB seeders and evaluators
│   └── requirements.txt      # Python dependencies
├── sample_data/              # Seed CSVs and ground truth labels
├── docker-compose.yml        # Multi-container orchestration
└── Makefile                  # Development task automation
```

## 📝 License

MIT

## 🙏 Acknowledgments

Built for the SG Hackathon 2026.
