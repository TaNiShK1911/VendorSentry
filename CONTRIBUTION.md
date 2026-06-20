# CONTRIBUTION.md — Backend Build Split (2 Developers)

Scope: **backend only** (frontend is built by others against `BACKEND_INTEGRATION.md`). Two developers, parallelized by clean ownership boundaries with one shared contract surface (DB models + Pydantic schemas) to avoid integration conflicts late in the hackathon.

## Team Split Rationale

The backend splits cleanly into two halves with a natural seam:
- **Dev A owns "truth": data, scoring, extraction** — everything that decides *what a vendor's risk actually is*
- **Dev B owns "delivery": API surface, monitoring/alerts, reporting** — everything that *exposes and acts on* that truth

This split minimizes merge conflicts (different files, different concerns) while keeping a single, jointly-owned contract layer (`models/`, `schemas/`) that both depend on and that's agreed up front.

---

## Dev A — Data Layer, Scoring Engine & AI Extraction

**Owns:** `backend/app/models/`, `backend/app/services/scoring/`, `backend/app/services/extraction/`, `backend/scripts/seed.py`, `backend/scripts/evaluate.py`

### Responsibilities
1. **DB schema & migrations** — `Vendor`, `VendorScore`, `ExtractionJob`, `ground_truth` tables (Alembic)
2. **CSV ingestion** — partial-failure-tolerant loader for `vendor_registry.csv` and `vendor_labels.csv` into separate tables
3. **Risk scoring engine** — pure functions implementing the weighted formula from `IMPLEMENTATION_PLAN.md` §4 (`breach_subscore`, `access_subscore`, `compliance_subscore`, `financial_subscore`, `composite`, `tiering`)
4. **LLM extraction service** — structured-JSON extraction from contract/cert text, grounding + conflict-detection logic
5. **Narrative generation** — post-scoring, fact-constrained rationale generation
6. **Evaluation harness** — `scripts/evaluate.py`: runs scoring over all 400 vendors, reports precision/recall per tier vs. `vendor_labels.csv`, with CRITICAL/HIGH recall called out

### Day-by-day (assuming a ~48hr hackathon)
- **Hrs 0–4:** DB models + migrations + seed script working end-to-end with raw CSV data (no scoring yet)
- **Hrs 4–14:** Scoring engine implemented + unit tests with fixture vendors; first evaluation run against ground truth, weight tuning
- **Hrs 14–24:** LLM extraction service (prompts, structured output parsing, conflict detection) wired to a manual trigger
- **Hrs 24–30:** Narrative generation; final evaluation harness polish with per-tier report
- **Hrs 30+:** Bug fixes, support Dev B's integration, help with demo data scenarios

### Definition of Done (for Dev A's modules)
- `python backend/scripts/seed.py` loads all 400 vendors with < 5% row failures, logged clearly
- `python backend/scripts/evaluate.py` runs and prints precision/recall per severity tier
- Scoring functions have unit tests covering each tier boundary condition
- Extraction service never lets the LLM set `composite_score` or `tier` directly (architectural rule, see `AGENT.md`)

---

## Dev B — API Layer, Monitoring, Alerts & Reporting

**Owns:** `backend/app/api/`, `backend/app/services/monitoring/`, `backend/app/services/alerts/`, `backend/app/services/reporting/`, Celery/Redis setup, Docker Compose

### Responsibilities
1. **FastAPI app skeleton** — app factory, routers, dependency injection, error handling, CORS for frontend
2. **Vendor & scoring endpoints** — CRUD on vendors, score retrieval/history, trigger-rescore endpoint (calls into Dev A's scoring engine)
3. **Monitoring sweeps (Celery beat)** — cert-expiry watcher, contract-expiry watcher, assessment-overdue watcher, mock breach-DB poller
4. **Alert system** — alert generation, dedup logic, alert feed + acknowledge/resolve endpoints
5. **Reporting** — portfolio aggregation endpoints (counts by tier, trend-over-time), audit report generator (Markdown → PDF), CSV export
6. **Infra** — Docker Compose (api, postgres, redis, worker, beat), `.env.example`

### Day-by-day
- **Hrs 0–4:** FastAPI skeleton + Docker Compose running, health-check endpoint, DB connection wired to Dev A's models as they land
- **Hrs 4–14:** Vendor CRUD + score endpoints (consumes Dev A's scoring engine as soon as it's testable)
- **Hrs 14–24:** Celery beat sweeps + mock breach-DB + alert generation/dedup
- **Hrs 24–34:** Reporting endpoints + PDF/Markdown report generator + portfolio aggregation
- **Hrs 34+:** Full API polish, `BACKEND_INTEGRATION.md` kept in sync, support frontend integration questions, demo scenario seeding (scripted "live breach" event for the demo)

### Definition of Done (for Dev B's modules)
- All endpoints in `BACKEND_INTEGRATION.md` implemented and match the documented contract exactly
- Swagger UI (`/docs`) fully reflects real schemas
- Alerts never duplicate for the same condition (dedup verified with a test that runs the sweep twice)
- `docker compose up` brings up the full stack with one command

---

## Shared Contract (agree on this in the first hour, before splitting off)

Both devs jointly author and freeze early:
1. **`backend/app/models/`** — table shapes (fields, types, relationships) — changes after hour 4 require a quick sync, not a silent edit
2. **`backend/app/schemas/`** — Pydantic request/response models — this **is** the API contract; Dev A's scoring output shape and Dev B's endpoint response shape must match exactly
3. **The scoring function signature** — Dev B needs to call `score_vendor(vendor: Vendor) -> VendorScore` without caring about its internals; agree on this signature before Dev A starts implementing internals, so Dev B can build against a stub immediately

### Stub-first integration pattern
Dev B should not wait on Dev A's real implementation:
```python
# Dev A provides this stub on hour 1, real implementation lands by hour 14
def score_vendor(vendor: Vendor) -> VendorScore:
    """STUB — returns a fixed mock score so Dev B can build endpoints immediately."""
    return VendorScore(vendor_id=vendor.id, composite_score=50, tier="MEDIUM", ...)
```
Dev B builds the full `/vendors/{id}/score` endpoint against this stub from hour 1, and it keeps working unmodified once Dev A swaps in the real engine — because both agreed on the function signature up front.

## Sync Points (keep these short, 10–15 min)
- **Hour 4:** Confirm DB models frozen enough to build on; confirm scoring function stub signature
- **Hour 14:** Dev A's real scoring engine replaces the stub — quick joint smoke test
- **Hour 24:** Extraction + alerts both live — confirm narrative/extraction output shape matches what reporting needs
- **Hour 34:** Full integration test — seed data → score → alert → report, all working end-to-end
- **Hour 42+:** Joint demo rehearsal, bug triage by whoever's free, not by original ownership

## Git Workflow
- `main` always deployable/demoable
- Feature branches: `dev-a/scoring-engine`, `dev-b/alerts-api`, etc.
- PRs reviewed by the other dev for anything touching the shared contract (`models/`, `schemas/`)
- Merge to `main` at each sync point, not continuously — keeps `main` demo-stable during the hackathon
