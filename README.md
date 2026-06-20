# VendorSentry — AI-Powered Third-Party & Vendor Risk Intelligence

> Track: Third-Party Risk & Governance | Approach: **A — AI-Powered Vendor Intelligence** | Difficulty: Advanced

VendorSentry is a direct implementation of **Option A — AI-Powered Vendor Intelligence**, not a generic vendor dashboard. It ingests vendor data from six source types — contract documents, security assessments/questionnaires, audit reports, certifications, breach databases, and public records/third-party status APIs — uses an LLM strictly for extraction, compliance summarization, and grounded narrative generation, and feeds everything into a deterministic risk-scoring engine that combines breach history, data access scope, compliance maturity, and financial stability. Scores recalculate dynamically whenever new evidence arrives, and the system surfaces it all through a Red/Yellow/Green portfolio dashboard with continuous monitoring and change alerts.

This repo's documentation set answers: *what are we building, why is it different, who builds what, and how does the frontend talk to it.* See [§"Why this matches Option A"](#why-this-matches-option-a) below for an explicit feature-to-component mapping.

## Document Map

| File | Purpose |
|---|---|
| [`PRD.md`](./PRD.md) | Product requirements — problem, users, scope, success metrics |
| [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) | Phased technical build plan, architecture, data pipeline, milestones |
| [`NOVELTY.md`](./NOVELTY.md) | What differentiates VendorSentry from other teams' submissions |
| [`AGENT.md`](./AGENT.md) | Conventions for any AI coding agent (Claude Code, Copilot, etc.) working in this repo |
| [`CONTRIBUTION.md`](./CONTRIBUTION.md) | 2-person backend split + integration protocol |
| [`BACKEND_INTEGRATION.md`](./BACKEND_INTEGRATION.md) | Full API contract for the frontend team |

## Problem Statement (condensed)

Enterprises track 1,000+ vendors with inconsistent spreadsheet-based risk assessment, no scoring system, and no way to answer "who has access to customer data?" in an audit. Breaches go unnoticed, contractor access outlives projects, and certifications expire silently. VendorSentry fixes this with continuous, AI-assisted, explainable scoring built on Option A's full multi-source pipeline.

## Data Ingestion Sources (Option A, in full)

VendorSentry ingests and reconciles **six** source types, per the Option A spec — not just the seeded CSVs:

| Source | What we pull | How |
|---|---|---|
| **Contract documents** | Data access permissions, SLAs, compliance requirements | LLM extraction (PDF/text upload) |
| **Security assessments / questionnaires** | Self-reported controls, scoping answers | LLM extraction → structured fields |
| **Audit reports** | SOC 2 Type I/II, ISO 27001, PCI-DSS attestations | LLM summarization → structured compliance record |
| **Certifications** | Type, issue date, expiry date, status | Structured ingestion + expiry watcher |
| **Breach databases** | Public breach disclosures matched to vendor | Mock breach-DB API poller (pluggable for real feeds post-hackathon) |
| **Public records** | Financial health signals, regulatory actions | Web-scraping/enrichment service (mocked for demo, real-adapter-ready) |
| **Third-party vendor integrations / APIs** | Live SOC 2 status, trust-center data (e.g., Vanta/Drata-style status APIs) | Status-check adapter, polled on a schedule |

Every one of these is a **structured-evidence input** to the deterministic scoring engine — none of them, including LLM output, is allowed to set a risk score directly. See `IMPLEMENTATION_PLAN.md` §3–4.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, PostgreSQL (SQLAlchemy + Alembic), Celery + Redis (background jobs)
- **AI Layer:** LLM API (Claude via Anthropic API / OpenRouter fallback) — used **only** for contract/assessment extraction, SOC 2/ISO 27001 compliance summarization, and post-scoring narrative generation; never for the score itself
- **Data Enrichment:** Web scraping / external-data-enrichment service for public records (financial health, regulatory actions), breach database APIs (mock + pluggable real adapters), third-party status-check APIs (SOC 2/ISO live status)
- **Data Processing:** Pandas for CSV ingestion, normalization, and the evaluation harness
- **Visualization:** Plotly/Recharts for portfolio charts, risk-history timelines, and trend views
- **Data Sources:** `vendor_registry.csv`, `vendor_labels.csv` (provided seed data), contract/assessment/audit PDFs, mock breach-DB API, mock public-records/financial-health API, mock SOC 2 status API
- **Frontend:** React + Recharts/Plotly (see `BACKEND_INTEGRATION.md` for the contract)
- **Infra:** Docker Compose for local dev

## Quickstart (planned)

```bash
git clone <repo>
cd vendor-risk-intel
cp .env.example .env          # add LLM API key, DB url
docker compose up --build     # spins up api, postgres, redis, worker
make seed                     # loads sample_data/vendor_registry.csv + vendor_labels.csv
open http://localhost:8000/docs   # FastAPI Swagger UI
```

## Repo Layout (planned)

```
vendor-risk-intel/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routers
│   │   ├── core/             # config, security, celery app
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── scoring/      # deterministic risk scoring engine
│   │   │   ├── extraction/   # LLM contract/assessment/audit-report extraction + narrative
│   │   │   ├── enrichment/   # web scraping / public records / financial-health adapters
│   │   │   ├── integrations/ # third-party status-check APIs (e.g., SOC 2 live status)
│   │   │   ├── monitoring/   # breach-DB poller + cert/contract expiry watchers + rescore triggers
│   │   │   └── alerts/       # alert generation + delivery (incl. risk-tier-change alerts)
│   │   └── main.py
│   ├── tests/
│   └── alembic/
├── sample_data/
│   ├── vendor_registry.csv
│   └── vendor_labels.csv
├── docs/                      # this documentation set
└── docker-compose.yml
```

## Success Criteria (from problem statement)

| Metric | Target |
|---|---|
| Vendor coverage | 95%+ tracked |
| Risk accuracy | 80%+ alignment with auditor judgment |
| Alert timeliness | 30+ days advance notice |
| Operational efficiency | "Is vendor X compliant?" answerable in 5 min |
| Audit readiness | Full risk report generated in 15 min |
| Recall on CRITICAL/HIGH | Prioritized over raw precision — missing a breached high-access vendor is the worst failure mode |

## Why This Matches Option A

| Option A requirement | VendorSentry component |
|---|---|
| Multi-source data ingestion (contracts, assessments, audit reports, certs, breach DBs, public records, third-party APIs) | `services/extraction/` (documents), `services/enrichment/` (public records/web scraping), `services/integrations/` (SOC 2 status APIs), `services/monitoring/` (breach-DB poller) |
| LLM extracts contract obligations (data access, SLAs, compliance requirements) | `services/extraction/contract_parser.py` |
| LLM summarizes SOC 2 / ISO 27001 into structured format | `services/extraction/compliance_summarizer.py` |
| LLM generates risk narratives | `services/extraction/narrative.py` — runs **after** scoring, grounded in subscores only |
| Scoring combines breach history + access scope + compliance maturity + financial stability | `services/scoring/engine.py` — deterministic, see `IMPLEMENTATION_PLAN.md` §4 |
| Dynamic recalculation when new info appears | `services/monitoring/rescore_trigger.py`, fired by extraction completion, new breach signal, or cert/status change |
| Red/Yellow/Green output with change alerts | `services/scoring/tiering.py` + `services/alerts/` (`SCORE_TIER_CHANGED` alert type) |
| Portfolio view, 100+ vendors | `GET /vendors` + `GET /portfolio/score-distribution` (see `BACKEND_INTEGRATION.md`) |
| New breach detection | `services/monitoring/breach_watcher.py` |
| Certification expiry tracking | `services/monitoring/cert_watcher.py` |

This table is intentionally line-for-line against the Option A spec — every bullet in the original problem statement has a named, owned component, not a vague "covered by the dashboard" claim.
