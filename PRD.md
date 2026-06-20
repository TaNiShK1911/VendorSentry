# PRD — VendorSentry: AI-Powered Third-Party & Vendor Risk Intelligence

## 1. Problem

Enterprises with 1,000+ vendors (cloud providers, contractors, software vendors, MSPs, payment processors) cannot reliably answer:
- "Who currently has access to customer data?"
- "Is vendor X still compliant?"
- "Did any of our vendors get breached recently?"

Today this lives in spreadsheets: inconsistent, stale, no scoring logic, and impossible to monitor continuously across hundreds of vendors. The consequences are real — undetected vendor breaches, orphaned contractor access sold to competitors, silently expired SOC 2 certifications, and failed audits under GDPR Art. 28/33, NIST SP 800-53 SA-9, and SOX 404.

## 2. Goal

Replace the spreadsheet with a system that:
1. **Inventories** every vendor and what they can access.
2. **Assesses** security posture and compliance using AI-assisted document understanding.
3. **Scores** each vendor on a transparent, weighted risk scale → Red/Yellow/Green.
4. **Monitors continuously** for breach signals and certification expiry.
5. **Alerts** proactively, 30+ days before something becomes a problem.
6. **Supports audits** with a report generated in minutes, not days.

## 3. Users / Personas

| Persona | Need |
|---|---|
| **CISO / Security Lead** | Portfolio-level view: which vendors are red, why, and what changed this week |
| **Vendor/Procurement Manager** | Per-vendor drill-down, contract terms, renegotiation leverage |
| **Auditor / Compliance Officer** | One-click evidence: access scope, cert status, breach history, remediation trail |
| **Incident Responder** | "Which vendors touch PII and were breached in the last 12 months?" answered instantly |

## 4. Scope (Hackathon MVP)

### In scope
- **Multi-source data ingestion** spanning all six Option A source types:
  1. CSV ingestion of `vendor_registry.csv` (400 vendors) and `vendor_labels.csv` (ground truth, evaluation-only)
  2. **Contract documents** (PDF/text upload) — LLM-extracted for data access, SLAs, compliance requirements
  3. **Security assessments / questionnaires** — LLM-extracted into structured control answers
  4. **Audit reports** (SOC 2 Type I/II, ISO 27001) — LLM-summarized into structured compliance fields
  5. **Certifications** — structured ingestion with type/issue/expiry/status, watched continuously
  6. **Breach databases** — mock breach-DB API polling, matched to vendors, pluggable for a real feed later
  7. **Public records** (financial health, regulatory issues) — web-scraping/enrichment adapter (mocked for demo)
  8. **Third-party vendor integrations / APIs** — status-check adapter for live SOC 2/ISO status (mocked, real-adapter-ready)
- Weighted, explainable risk-scoring engine (breach history + data access scope + compliance maturity + financial stability + contract status)
- LLM-generated plain-English risk narratives per vendor, produced **after** scoring and grounded only in structured facts
- Continuous monitoring: cert-expiry watcher, breach-signal watcher (mock breach DB), financial/regulatory-signal watcher, risk-tier-change detection, and automatic rescoring whenever any of the above sources delivers new evidence
- Alerting: contract expiring (60d), cert expiring, assessment overdue, new breach detected, **risk tier changed**
- Dashboard: portfolio grid for 100+ vendors sorted by risk, filters, drill-down, Red/Yellow/Green status, risk-history/change timeline, CSV export
- Audit report generator (PDF/Markdown) summarizing a vendor or the full portfolio

### Out of scope (post-hackathon)
- Live integrations with real breach-intelligence feeds (HaveIBeenPwned-Enterprise, etc.) — mocked for demo
- Real ITSM/procurement system integrations (Jira, ServiceNow, Coupa) — stubbed as recommendations
- Multi-tenant auth/RBAC beyond a basic role model
- Native e-signature / contract negotiation workflow

## 5. Functional Requirements

### FR1 — Vendor Registry
- CRUD on vendor records (name, type, contract dates, certifications + expiry, data access scope, breach status, annual spend, risk score)
- Bulk import from CSV with validation + dedup
- Full history of changes per vendor (audit trail)

### FR2 — AI Extraction Pipeline (LLM: extraction + summarization + narrative ONLY)
- **Contract obligation extraction:** given a contract document (text or PDF), extract data access permissions, SLA terms, and compliance requirements into structured JSON — this is the "Extract contract obligations using NLP" requirement from Option A
- **Compliance evidence summarization:** given a SOC 2 / ISO 27001 audit report or security-assessment questionnaire, parse and summarize it into the same structured compliance schema (cert type, scope, findings, exceptions) — this is the "Summarize vendor compliance" requirement
- **Public-record / status-API normalization:** structured-ize financial-health and regulatory-action signals pulled from the enrichment/integrations layer into the same evidence schema, so all six source types land in one consistent structured representation
- **Grounded narrative generation:** generate a 2–4 sentence plain-English risk narrative per vendor (e.g., *"Vendor has SOC 2 Type II but uses older encryption"*) — generated strictly **after** the deterministic score is computed, using only the already-computed subscores and structured facts as input
- **Hard constraints on the LLM layer:**
  - Never invents a certification, date, or fact not present in the source material
  - Never outputs a risk score or tier directly — extraction and narrative only, scoring is a separate deterministic function (see FR3)
  - Any disagreement between a new extraction and existing structured data is written as a `conflict` record and surfaced to the user — never silently resolved or overwritten
- Parse and normalize unstructured "notes"/"explanation" fields from `vendor_labels.csv` into the same structured schema (evaluation-only, never feeds scoring)

### FR3 — Risk Scoring Engine
- Deterministic, explainable formula that **combines exactly the four factors Option A specifies**: breach history + data access scope + compliance maturity + financial stability (see `IMPLEMENTATION_PLAN.md` §4 for the exact weighted formula)
- Recency-weighted breach impact (a breach 5 years ago counts less than one 2 months ago)
- **Dynamically recalculates** whenever new evidence appears from *any* of the six ingestion sources — a new contract clause, a renewed cert, a breach-DB hit, a updated financial-health signal, or a status-API change all trigger an automatic rescore, not just manual edits
- Output is always one of **Red (CRITICAL/HIGH) / Yellow (MEDIUM/LOW) / Green (CLEAR)**, with the underlying five-tier breakdown available on drill-down
- Every score ships with a **rationale**: which factors drove it and by how much, and which evidence source contributed each fact
- The LLM never touches this formula — it is pure, testable code; AI-derived facts are just another structured input alongside CSV fields

### FR4 — Monitoring & Alerts
- Daily (simulated) sweep for: certs expiring within 30/60 days, contracts expiring within 60 days, assessments overdue (>12 months since last review)
- **New breach detection:** continuous polling of the breach-database adapter, matched to vendors by name/domain, triggers an automatic rescore the moment a match is found
- **Certification expiry tracking:** every certification's expiry date is watched on a schedule; escalating alerts at 60/30/7 days out
- **Continuous rescoring:** any new document extraction, status-API change, or breach/financial signal triggers an immediate recompute — the score is never allowed to go stale silently
- **Change alerts:** a dedicated `SCORE_TIER_CHANGED` alert fires whenever a vendor's tier moves (e.g., MEDIUM → HIGH), independent of the underlying cause, so a CISO can subscribe to "tell me when anything gets worse" without tracking every individual signal
- Alert dedup so the same condition doesn't re-fire daily
- Alert delivery via API + (stretch) email digest

### FR5 — Dashboard / Portfolio View
- **Portfolio view for 100+ vendors:** sortable/filterable grid showing vendor, type, risk tier, score, last reviewed, key flags — "see who's risky at a glance" per Option A
- **Red/Yellow/Green status:** primary visual signal on every vendor row and in the portfolio summary widget
- **Vendor drill-down:** full risk narrative, score breakdown by factor, access map, contract terms, certification status, alert history
- **Breach alerts:** dedicated feed/badge for new-breach-detected events, filterable by severity
- **Certification tracking:** per-vendor and portfolio-wide view of cert status and upcoming expirations
- **Risk history / change timeline:** per-vendor score-over-time chart plus a portfolio-wide trend chart, so "what changed this week" is answerable visually, not just in a log
- "Tiered response" framing — not pass/fail; bucketed into CRITICAL / HIGH / MEDIUM / LOW / CLEAR per the labeled anomaly taxonomy, rolled up to Red/Yellow/Green for the headline view

### FR6 — Reporting
- One-click audit report per vendor and for the full portfolio (risk-by-category, trending, recommendations)
- Export to CSV/PDF

## 6. Non-Functional Requirements

- **Explainability:** every AI-assisted score/narrative must be traceable to source fields — no black-box numbers
- **Latency:** dashboard list view < 1s for 1,000 vendors; "Is vendor X compliant?" answerable in under 5 minutes end-to-end (i.e., effectively instant once data is ingested)
- **Recall priority:** for CRITICAL/HIGH severity, recall > precision — false negatives (missed breached high-access vendor) are the costliest failure mode
- **Auditability:** every score change and alert is logged with timestamp + triggering input

## 7. Data

| File | Records | Use |
|---|---|---|
| `vendor_registry.csv` | 400 | Primary seed: type, certifications + expiry, breach status, risk score, annual spend, contract dates |
| `vendor_labels.csv` | 400 | Ground truth for evaluation: `is_anomaly`, `anomaly_type`, `severity`, `expired_certifications`, `explanation` |

Anomaly taxonomy used for tiering (per problem statement):

| Type | Severity |
|---|---|
| `BREACHED_VENDOR_HIGH_ACCESS` | CRITICAL |
| `VENDOR_UNDER_INVESTIGATION` | CRITICAL |
| `HIGH_RISK_SCORE` (>80) | HIGH |
| `EXPIRED_CERTIFICATION` | HIGH/MEDIUM |
| `RECENTLY_BREACHED_VENDOR` | MEDIUM |
| `CONTRACT_EXPIRED_ACTIVE_ACCESS` | MEDIUM |
| `ELEVATED_RISK_VENDOR` (65–80) | LOW |

## 8. Success Metrics (Demo-Day Evaluation)

| Metric | Target |
|---|---|
| Vendor coverage | 95%+ of seeded vendors tracked with a current score |
| Risk accuracy | 80%+ agreement between system tier and `vendor_labels.csv` ground truth |
| Recall on CRITICAL/HIGH | Maximize — explicit eval focus per problem statement |
| Alert timeliness | All cert/contract alerts fire ≥30 days before expiry |
| Time to answer "Is vendor X compliant?" | < 5 min |
| Time to generate full audit report | < 15 min |

## 9. Why This Matches Option A

| Option A requirement (verbatim from problem statement) | PRD section / system component |
|---|---|
| Data ingestion: contract documents | FR2 — contract obligation extraction |
| Data ingestion: security assessments, audit reports, certifications | FR2 — compliance evidence summarization; FR1 — certification fields |
| Data ingestion: breach databases | FR4 — breach-DB watcher |
| Data ingestion: public records (financial health, regulatory) | §4 In-scope item 7 — enrichment adapter |
| Data ingestion: third-party integrations (SOC 2 status API) | §4 In-scope item 8 — status-check adapter |
| LLM extracts contract obligations (data access permissions) | FR2 |
| LLM summarizes SOC 2 / ISO 27001 into structured format | FR2 |
| LLM generates risk narratives | FR2 — grounded, post-scoring |
| Scoring combines breach + access + compliance + financial | FR3 |
| Dynamic recalculation when new info appears | FR3, FR4 |
| Red/Yellow/Green output with change alerts | FR3, FR5, FR4 (`SCORE_TIER_CHANGED`) |
| Dashboard: portfolio view, 100+ vendors | FR5 |
| Dashboard: new breach detection | FR4, FR5 |
| Dashboard: certification tracking | FR4, FR5 |

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucinates a certification/date that isn't in the source | Extraction outputs are validated against structured CSV fields before being trusted; narrative generation is grounded with retrieved facts only, and conflicts are flagged, not silently resolved |
| Conflicting info (vendor claims current SOC2, but expired) | Score always uses the verified/structured expiry date; conflicting self-reported claims are surfaced as a separate "disputed" flag, never silently overridden |
| Demo breaks on bad/missing CSV rows | Defensive ingestion: partial-row tolerance, row-level error log, ingestion never fails the whole batch |
| Score weights feel arbitrary to judges | Every weight and its justification documented in `IMPLEMENTATION_PLAN.md`; rationale shown per-vendor in UI |
| Public-records/status-API sources are inherently unreliable or rate-limited live | Enrichment and integration adapters are built behind a clean interface with mocked implementations for the demo; real adapters are swappable post-hackathon without touching scoring logic |
