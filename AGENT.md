# AGENT.md — Working Agreement for AI Coding Agents

This file orients any AI coding agent (Claude Code, Copilot, Cursor, etc.) operating in this repository. Read this before making changes.

## Project Identity
VendorSentry — AI-powered third-party vendor risk scoring system. See `PRD.md` for requirements, `IMPLEMENTATION_PLAN.md` for architecture, `BACKEND_INTEGRATION.md` for the API contract the frontend depends on.

## Hard Rules

1. **Never let the LLM output the risk score directly.** Scoring is a deterministic function in `backend/app/services/scoring/`. The LLM layer (`services/extraction/`) only produces structured facts and narratives. If you're tempted to have a prompt "just return a risk score," stop — that violates the core architectural decision in `IMPLEMENTATION_PLAN.md` §8.
2. **Ground truth (`vendor_labels.csv`) is evaluation-only.** Never wire it into the live scoring path. It's loaded into a separate `ground_truth` table and read only by `scripts/evaluate.py`.
3. **Conflicts are surfaced, never silently resolved.** If extracted data disagrees with structured fields, write both and flag it — don't pick one and discard the other.
4. **Every API change must update `BACKEND_INTEGRATION.md`.** The frontend is built against that contract; treat it as the source of truth alongside the actual OpenAPI schema. Breaking changes need a version bump or explicit notice in that file.
5. **Don't break the evaluation harness.** `backend/scripts/evaluate.py` must keep running against the seeded data and reporting per-tier precision/recall. If you touch scoring logic, re-run it and report the before/after numbers in your PR description / commit message.
6. **CSV ingestion must be partial-failure tolerant.** A malformed row logs an error and is skipped; it never aborts the whole batch (per `IMPLEMENTATION_PLAN.md` §3 and `PRD.md` §9 risk table).

## Code Conventions

- Python 3.11, type hints everywhere, `pydantic` for all request/response and structured-extraction schemas
- FastAPI routers live under `backend/app/api/`, one file per resource (`vendors.py`, `scoring.py`, `alerts.py`, `reports.py`, `extraction.py`)
- Business logic does not live in route handlers — routes call into `services/`, which are plain, unit-testable functions/classes
- DB access only through SQLAlchemy models in `models/`; no raw SQL outside of migrations unless performance-justified and commented
- All Celery tasks are idempotent (safe to re-run) — monitoring sweeps must use `dedup_key` logic, never assume "this only runs once"
- Tests: `pytest`, colocated under `backend/tests/`, mirroring the `app/` structure. Scoring logic requires unit tests with concrete vendor fixtures (not just mocks)

## Where Things Live (don't guess, check first)

| Concern | Location |
|---|---|
| Risk scoring formula | `backend/app/services/scoring/engine.py` |
| Tiering / anomaly-type mapping | `backend/app/services/scoring/tiering.py` |
| LLM extraction prompts | `backend/app/services/extraction/prompts.py` |
| Narrative generation | `backend/app/services/extraction/narrative.py` |
| Monitoring sweeps | `backend/app/services/monitoring/` |
| Alert dedup | `backend/app/services/alerts/dedup.py` |
| API schemas (request/response) | `backend/app/schemas/` |
| DB models | `backend/app/models/` |
| Evaluation harness | `backend/scripts/evaluate.py` |
| Seed/ingestion script | `backend/scripts/seed.py` |

## Before Opening a PR / Finishing a Task

- [ ] `pytest backend/tests` passes
- [ ] If scoring logic changed: `python backend/scripts/evaluate.py` re-run, recall on CRITICAL/HIGH not regressed
- [ ] If an endpoint changed: `BACKEND_INTEGRATION.md` updated to match
- [ ] No secrets/API keys committed; LLM API key only via `.env` (see `.env.example`)
- [ ] New Celery tasks are idempotent and deduped

## Things Not to Build (out of scope per PRD §4)
- Real third-party breach-intel integrations (mock only)
- Real ITSM/procurement integrations (stub/recommend only)
- Full multi-tenant RBAC (basic roles only)
- E-signature / contract negotiation workflows

## Communication Style for Agent Output
When summarizing work in this repo, be concrete: name the file changed, the function, and — for anything touching scoring — the actual before/after recall numbers from the evaluation harness. Avoid vague "improved the risk engine" summaries.
