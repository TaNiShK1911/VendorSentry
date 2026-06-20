# Implementation Plan — VendorSentry

## 1. Architecture Overview

```
                         ┌──────────────────────────┐
                         │        Frontend (React)   │
                         └─────────────┬─────────────┘
                                        │ REST (JSON)
                         ┌─────────────▼─────────────┐
                         │       FastAPI Backend      │
                         │  /vendors /scoring /alerts │
                         │  /extract /reports /search │
                         └──┬───────┬───────┬─────────┘
                            │       │       │
              ┌─────────────┘   ┌───▼───┐  ┌▼──────────────┐
              │                 │ Redis │  │  PostgreSQL    │
   ┌──────────▼─────────┐       │ queue │  │  (vendors,     │
   │  Celery Workers     │◄──────┘       │  │  scores,       │
   │  - extraction job   │               │  │  alerts,       │
   │  - scoring recompute│               │  │  audit_log)    │
   │  - monitoring sweep │───────────────┘  └────────────────┘
   └─┬────┬─────┬────┬───┘
     │    │     │    │
┌────▼┐ ┌─▼───┐┌▼───┐┌▼─────────────┐
│ LLM ││Breach││Cert││ Enrichment / │
│ API ││ DB   ││Watch││ Integrations │
│(extr││ API  ││ er  ││ (public      │
│act +││(poll)││     ││ records,     │
│narr.)││      ││     ││ SOC2 status) │
└─────┘└──────┘└─────┘└──────────────┘
```

**Six ingestion sources feed the pipeline (Option A, full scope):** contract documents, security assessments/questionnaires, audit reports, certifications, breach databases, and public records/third-party status APIs — see §3. All are normalized into the same structured-evidence schema before they ever reach the scoring engine. The LLM only ever sits in the **extraction/narrative** path (top-left); the scoring engine (inside the API/Celery layer) is pure deterministic code with no LLM in its call path.

## 2. Data Model (core entities)

```
Vendor
 ├─ id, name, type, contact, annual_spend
 ├─ contract_start, contract_end, contract_status
 ├─ certifications: [{ type: SOC2|ISO27001|PCI-DSS, status, issued_date, expiry_date, source: manual|audit_report|status_api }]
 ├─ data_access_scope: { pii: bool, financial: bool, systems: [...], scope_notes }
 ├─ breach_history: [{ date, severity, source: breach_db|manual, description, resolved: bool }]
 ├─ financial_health_signal: enum(stable, watch, distressed, unknown)
 ├─ financial_health_source: enum(public_records_enrichment, manual, unknown)
 ├─ last_assessed_at
 └─ current_score → VendorScore (1:1, latest)

VendorScore
 ├─ vendor_id, computed_at
 ├─ breach_subscore, access_subscore, compliance_subscore, financial_subscore
 ├─ composite_score (0-100), tier (CRITICAL|HIGH|MEDIUM|LOW|CLEAR), status_color (RED|YELLOW|GREEN)
 ├─ anomaly_types: [string]   # maps to taxonomy in PRD
 ├─ rationale (LLM-generated narrative, grounded, post-scoring)
 ├─ triggered_by (enum: manual|extraction_complete|breach_detected|cert_status_change|financial_signal_change|scheduled_sweep)
 └─ previous_score_id (for trend/delta)

Alert
 ├─ id, vendor_id, type (CERT_EXPIRING|CONTRACT_EXPIRING|ASSESSMENT_OVERDUE|NEW_BREACH|SCORE_TIER_CHANGED)
 ├─ severity, message, created_at, acknowledged_at, resolved_at
 └─ dedup_key (prevents re-firing same condition)

ExtractionJob
 ├─ id, vendor_id, source_type (csv_row|contract_pdf|security_assessment|audit_report|manual_note)
 ├─ raw_text, structured_output (JSON), confidence, flagged_conflicts
 └─ status (pending|done|failed)

EvidenceSignal
 ├─ id, vendor_id, source (breach_db|public_records|status_api|extraction_job)
 ├─ signal_type (new_breach|financial_health_change|cert_status_change|regulatory_action)
 ├─ payload (JSON, raw signal as received), received_at
 └─ consumed_by_score_id (links to the VendorScore it triggered, if any)

AuditLogEntry
 ├─ id, entity_type, entity_id, change_type, before, after, actor, timestamp
```

`EvidenceSignal` is the unifying table for the breach-DB poller, the public-records enrichment adapter, and the third-party status-check API — every external signal that isn't a direct document upload lands here first, then triggers extraction normalization (if unstructured) and a rescore.

## 3. Ingestion & Extraction Pipeline (all six Option A sources)

1. **CSV Ingest** (`vendor_registry.csv`, `vendor_labels.csv`) — bulk seed
   - Row-level validation (required fields, date parsing, enum normalization)
   - Upsert into `Vendor`; partial failures logged per-row, batch never aborts
   - `vendor_labels.csv` loaded into a separate `ground_truth` table — used only for evaluation, never fed into the live scoring engine (avoids leakage / circular scoring)

2. **Contract Documents** (PDF/text upload, ad hoc per vendor)
   - LLM extraction job pulls **data access permissions, SLA terms, and compliance requirements** into structured JSON — directly fulfills Option A's "Extract contract obligations using NLP" bullet

3. **Security Assessments / Questionnaires** (PDF/text upload)
   - Same extraction pipeline, different prompt template tuned for Q&A-style self-assessment documents; output normalized into the same `data_access` / `compliance_claims` schema as contracts

4. **Audit Reports** (SOC 2 Type I/II, ISO 27001, PCI-DSS reports)
   - LLM summarization job parses report structure (scope, opinion, exceptions/findings, period covered) into structured compliance fields — fulfills "Summarize vendor compliance... parse SOC 2, ISO 27001 reports into structured format"

5. **Certifications** (structured metadata, either manual entry or extracted from #4)
   - Stored directly with type/status/issued/expiry; feeds both `compliance_subscore` and the cert-expiry watcher (§5)

6. **Breach Databases** (mock API, polled on a schedule)
   - New signals land in `EvidenceSignal` (source=`breach_db`), matched to vendors by name/domain, appended to `breach_history`, and trigger an immediate rescore + `NEW_BREACH` alert

7. **Public Records** (financial health, regulatory issues — web-scraping/enrichment adapter)
   - A pluggable `enrichment` service queries a (mocked, for the hackathon) public-records source per vendor on a schedule; output normalized to `financial_health_signal` + any regulatory-action flags, landing in `EvidenceSignal` (source=`public_records`)

8. **Third-Party Integrations** (vendor's own status API, e.g. SOC 2 live-status from a trust-center-style endpoint)
   - An `integrations` adapter polls each vendor's declared status-check endpoint (mocked for the hackathon, real-adapter-ready), comparing live status against our stored certification record — any mismatch becomes a `conflict`, not a silent update

**Common extraction contract (sources 2–4):**
- Prompt the LLM with the vendor's structured fields + the new free-text/document content, and require **strict JSON** output: `{data_access, compliance_claims, sla_terms, conflicts: []}`
- **Grounding rule:** the LLM is only allowed to assert facts present in the input; any certification/date it states must be cross-checked against existing structured fields post-hoc — mismatches become a `conflicts` entry, not a silent overwrite. This applies identically whether the new evidence came from a document upload, a freshly-summarized audit report, or a status-API mismatch.
- Output stored on `ExtractionJob`, then merged into `Vendor` fields with conflicts surfaced (never auto-resolved)

**Narrative Generation (after, never before, scoring):**
- Separate, smaller LLM call: given the *already-computed* subscores + structured facts (from whichever of the eight sources above contributed them), produce a 2–4 sentence rationale, e.g. *"Vendor has SOC 2 Type II but uses older encryption"* — the canonical Option A example output
- Narrative generation never sees raw/unverified document text directly — only the post-extraction, post-conflict-check structured facts — so it cannot narrate a hallucinated claim into existence

## 4. Risk Scoring Engine (deterministic core + AI-assisted inputs)

This is a direct implementation of Option A's "Risk scoring engine: Combine breach history + data access scope + compliance maturity + financial stability; dynamically recalculate when new info appears; output Red/Yellow/Green with change alerts." The composite score is a weighted sum of exactly these four sub-scores, each 0–100:

```
composite = 0.40 * breach_subscore        # breach history
          + 0.25 * access_subscore        # data access scope
          + 0.20 * compliance_subscore    # compliance maturity
          + 0.15 * financial_subscore     # financial stability
```

Every input to every subscore can originate from any of the eight ingestion paths in §3 — a `breach_subscore` update might come from the breach-DB poller or a manually logged incident; a `compliance_subscore` update might come from a renewed cert, a freshly summarized audit report, or a status-API confirmation. The formula itself never changes based on source — only the underlying fact does. This is what makes recalculation "dynamic": **any** accepted new fact re-runs the same deterministic formula.

**breach_subscore** — recency-decayed:
```
for each breach: contribution = severity_weight * exp(-months_since_breach / 12)
breach_subscore = min(100, sum(contributions) * 100)
```
`severity_weight`: CRITICAL=1.0, HIGH=0.7, MEDIUM=0.4, LOW=0.2. An active investigation forces `breach_subscore = 100` regardless of decay.

**access_subscore** — based on data sensitivity:
```
base = 20
+ 40 if pii_access
+ 30 if financial_access
+ 10 if broad_system_access (vs scoped)
```

**compliance_subscore**:
```
100 - (40 if any required cert expired)
    - (20 if cert expiring within 30 days, not yet renewed)
    - (15 if assessment overdue >12mo)
    floor at 0
```

**financial_subscore**: `stable=10, watch=50, distressed=90, unknown=40` (unknown is penalized — absence of signal is itself a risk)

**Tiering** (matches the provided anomaly taxonomy so eval recall is measurable):

| Condition | Tier |
|---|---|
| Breach in last 12mo AND (pii or financial access) | CRITICAL — `BREACHED_VENDOR_HIGH_ACCESS` |
| `under_investigation` flag | CRITICAL — `VENDOR_UNDER_INVESTIGATION` |
| composite > 80 | HIGH — `HIGH_RISK_SCORE` |
| required cert expired AND sensitive access | HIGH/MEDIUM — `EXPIRED_CERTIFICATION` |
| breach in last 12mo, lower scope | MEDIUM — `RECENTLY_BREACHED_VENDOR` |
| contract_end < today AND access still active | MEDIUM — `CONTRACT_EXPIRED_ACTIVE_ACCESS` |
| composite 65–80 | LOW — `ELEVATED_RISK_VENDOR` |
| else | CLEAR |

Tier rules are evaluated in priority order (CRITICAL conditions checked first) so a vendor can be multi-flagged but always reports its highest tier.

**Red/Yellow/Green rollup** (the headline status Option A asks for; the five-tier breakdown remains available on drill-down):

| Tier | Status Color |
|---|---|
| CRITICAL, HIGH | 🔴 Red |
| MEDIUM, LOW | 🟡 Yellow |
| CLEAR | 🟢 Green |

## 5. Monitoring & Alerting

Implements Option A's "new breach detection (monitor public breach databases)" and "certification tracking (when SOC 2 expires?)" requirements, plus the dynamic-recalculation and change-alert pieces of the scoring spec:

- Celery beat schedule (simulated "daily sweep") re-evaluates:
  - **Certification expiry tracking** — cert expiry within 60/30/7 days → escalating alert severity
  - Contract expiry within 60 days
  - Assessment overdue (>12 months since `last_assessed_at`)
  - **New breach detection** — mock breach-DB poll → new breach matched by vendor name/domain → `NEW_BREACH` alert + forced rescore
  - **Status-API drift** — third-party SOC 2/ISO status endpoint disagrees with stored cert status → `conflict` raised, not auto-applied
  - **Public-records sweep** — enrichment adapter re-checks financial-health/regulatory signals → `EvidenceSignal` recorded, triggers rescore if changed
- **Continuous rescoring:** any of the above producing a new or changed `EvidenceSignal` (or a completed `ExtractionJob`) triggers `services/scoring/engine.py` immediately — scores are never left stale between sweeps when a real-time signal arrives via the API (e.g., a contract upload)
- **Change alerts:** a `SCORE_TIER_CHANGED` alert fires whenever `VendorScore.tier` differs from `previous_score_id`'s tier, regardless of which underlying factor moved — this is the system-level "tell me when something gets worse" signal Option A's "change alerts" bullet calls for
- All alerts deduped via `dedup_key = hash(vendor_id, type, trigger_value)` so the same condition doesn't spam daily

## 6. Phased Build Plan

### Phase 0 — Setup (Hours 0–3)
- Repo scaffold, Docker Compose (api + postgres + redis + worker), `.env.example`
- DB schema + Alembic migration for core entities
- CSV ingestion script + seed command

### Phase 1 — Core Scoring (Hours 3–14)
- Implement deterministic scoring engine (pure functions, fully unit-testable against `vendor_labels.csv`)
- `/vendors` CRUD endpoints + `/vendors/{id}/score` endpoint
- Run scoring against all 400 seeded vendors, compare tiers to ground truth, tune weights

### Phase 2 — AI Extraction Layer + Enrichment Adapters (Hours 14–26)
- LLM extraction service (structured JSON output, grounding/conflict-check logic) covering contracts, security assessments, and audit reports
- Narrative generation service
- Mock public-records enrichment adapter (financial health, regulatory signals) and mock third-party status-API adapter (SOC 2 live status), both behind a clean interface for later real-source swap-in
- Wire extraction + enrichment into ingestion pipeline; expose `/vendors/{id}/extract` for ad-hoc document upload

### Phase 3 — Monitoring & Alerts (Hours 26–34)
- Celery beat sweep jobs: mock breach-DB poll, cert-expiry watcher, status-API drift check, public-records sweep
- `/alerts` endpoints, dedup logic, alert feed, `SCORE_TIER_CHANGED` change-alert logic

### Phase 4 — Reporting & Dashboard API (Hours 34–42)
- Portfolio aggregation endpoints (counts by tier, trend-over-time)
- Audit report generator (Markdown → PDF)
- `/reports` endpoints, CSV export

### Phase 5 — Polish & Demo (Hours 42–50)
- Evaluation harness: compute precision/recall vs `vendor_labels.csv`, especially CRITICAL/HIGH recall
- Seed a few "live" scenario vendors for the demo (a fresh breach fires mid-demo, a cert expires live)
- README polish, demo script, fallback recorded video

## 7. Evaluation Harness

A standalone script (`backend/scripts/evaluate.py`) that:
1. Runs the scoring engine over all vendors in `vendor_registry.csv`
2. Compares resulting `anomaly_types`/tier against `vendor_labels.csv`
3. Reports precision/recall/F1 **per severity tier**, with CRITICAL/HIGH recall called out explicitly (the stated eval priority)
4. Outputs a confusion-style breakdown so weight-tuning is data-driven, not guesswork

## 8. Why This Matches Option A

| Option A line item | Implementation component |
|---|---|
| Contract documents → data access, SLAs, compliance requirements | §3.2 — contract extraction job |
| Security assessments, audit reports, certifications | §3.3–3.5 — assessment/audit-report extraction, cert storage |
| Breach databases | §3.6 — breach-DB poller → `EvidenceSignal` |
| Public records (financial health, regulatory) | §3.7 — enrichment adapter → `EvidenceSignal` |
| Third-party integrations (SOC 2 status API) | §3.8 — integrations adapter, conflict-checked against stored certs |
| Extract contract obligations via NLP | §3 "Common extraction contract" |
| Summarize SOC 2 / ISO 27001 into structured format | §3.4 |
| Generate risk narratives | §3 "Narrative Generation" — post-scoring, grounded |
| Combine breach + access + compliance + financial | §4 formula |
| Dynamically recalculate on new info | §4 closing paragraph; §5 "Continuous rescoring" |
| Red/Yellow/Green output | §4 "Red/Yellow/Green rollup" table |
| Change alerts | §5 "Change alerts" (`SCORE_TIER_CHANGED`) |
| New breach detection (monitor breach DBs) | §5, first bullet group |
| Certification tracking (expiry) | §5, "Certification expiry tracking" |
| Stack: Python, LLM API, web scraping, breach DB APIs, Pandas, Plotly | `README.md` Tech Stack section |

## 9. Key Engineering Decisions

- **Deterministic core, AI-assisted edges:** the score itself is a pure, auditable function — the LLM only extracts/summarizes/narrates, it never directly outputs a number. This keeps the system explainable and prevents prompt-injection-via-contract-text from manipulating a vendor's actual risk score.
- **Conflicts are surfaced, not resolved:** when self-reported vendor claims disagree with structured data, both are stored and the discrepancy itself becomes a (minor) risk signal.
- **Ground truth never touches scoring:** `vendor_labels.csv` is evaluation-only, kept in a separate table, to avoid leaking the answer key into the live system.
