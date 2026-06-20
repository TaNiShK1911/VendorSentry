# BACKEND_INTEGRATION.md — API Contract for Frontend

Base URL (local dev): `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/docs` (Swagger), `http://localhost:8000/redoc`
Auth: `Authorization: Bearer <token>` header (basic role-based auth; see §8). Not required to hit `/docs`.
Content type: `application/json` everywhere except file upload/export endpoints.

## 0. Conventions

- All IDs are UUID strings.
- All timestamps are ISO 8601 UTC, e.g. `2026-06-20T07:09:00Z`.
- All list endpoints support `?page=1&page_size=25` and return the pagination envelope shown in §1.
- Risk tiers, in priority order: `CRITICAL > HIGH > MEDIUM > LOW > CLEAR`. Always render this order in any sorted/grouped UI.
- Error shape (all non-2xx responses):
```json
{
  "error": {
    "code": "VENDOR_NOT_FOUND",
    "message": "Vendor with id ... was not found",
    "details": {}
  }
}
```

## 1. Pagination Envelope (all list endpoints)

```json
{
  "items": [ /* resource objects */ ],
  "page": 1,
  "page_size": 25,
  "total_items": 412,
  "total_pages": 17
}
```

## 2. Vendors

### `GET /vendors`
List/search/filter vendors — backs the main portfolio grid.

**Query params:**
| Param | Type | Notes |
|---|---|---|
| `q` | string | free-text search on name |
| `tier` | string | `CRITICAL,HIGH,MEDIUM,LOW,CLEAR` (comma-separated, multi-select) |
| `type` | string | vendor type filter, e.g. `cloud_provider`, `contractor`, `mss_provider`, `payment_processor` |
| `min_score` / `max_score` | int | composite score range |
| `has_pii_access` | bool | |
| `cert_expiring_within_days` | int | e.g. `60` |
| `sort` | string | `score_desc` (default), `score_asc`, `name_asc`, `last_assessed_desc` |
| `page`, `page_size` | int | pagination |

**Response 200:** pagination envelope of `VendorListItem`:
```json
{
  "id": "uuid",
  "name": "Acme Cloud Storage",
  "type": "cloud_provider",
  "tier": "HIGH",
  "status_color": "RED",
  "composite_score": 84,
  "anomaly_types": ["HIGH_RISK_SCORE"],
  "last_assessed_at": "2026-05-01T00:00:00Z",
  "contract_end": "2026-12-31",
  "has_pii_access": true,
  "active_alert_count": 2
}
```
`status_color` is `RED | YELLOW | GREEN` — the headline Option A signal; `tier` is the underlying five-value breakdown. Lead UI with `status_color`.

### `GET /vendors/{vendor_id}`
Full vendor profile — drill-down view.

**Response 200:** `VendorDetail`:
```json
{
  "id": "uuid",
  "name": "Acme Cloud Storage",
  "type": "cloud_provider",
  "contact": { "liaison_name": "Jane Doe", "email": "jane@acme.com" },
  "annual_spend": 240000,
  "contract_start": "2024-01-01",
  "contract_end": "2026-12-31",
  "contract_status": "active",
  "certifications": [
    { "type": "SOC2_TYPE2", "status": "expired", "issued_date": "2023-06-01", "expiry_date": "2025-06-01", "source": "audit_report" }
  ],
  "data_access_scope": {
    "pii": true,
    "financial": false,
    "systems": ["customer_db", "object_storage"],
    "scope_notes": "Full read access to customer records bucket"
  },
  "breach_history": [
    { "date": "2026-02-14", "severity": "HIGH", "source": "breach_db", "description": "Unauthorized access to staging bucket", "resolved": false }
  ],
  "financial_health_signal": "watch",
  "financial_health_source": "public_records_enrichment",
  "last_assessed_at": "2026-05-01T00:00:00Z",
  "current_score": { /* VendorScore, see §3 */ },
  "score_history": [ /* array of VendorScore, most recent first */ ]
}
```

### `POST /vendors`
Create a vendor manually. Body mirrors `VendorDetail` minus computed fields (`current_score`, `score_history`).

### `PATCH /vendors/{vendor_id}`
Partial update. Triggers async rescore (see §3 "Rescore Trigger").

### `DELETE /vendors/{vendor_id}`
Soft-delete (sets `archived_at`); excluded from default list results.

### `POST /vendors/import`
Multipart CSV upload (`vendor_registry.csv` shape). Returns an `ImportResult`:
```json
{
  "rows_processed": 400,
  "rows_succeeded": 396,
  "rows_failed": 4,
  "errors": [{ "row": 57, "reason": "invalid contract_end date format" }]
}
```

## 3. Scoring

### `GET /vendors/{vendor_id}/score`
Latest score with full breakdown. **This is the "why is it risky" endpoint** — render every field, don't summarize.

```json
{
  "vendor_id": "uuid",
  "computed_at": "2026-06-20T06:00:00Z",
  "composite_score": 84,
  "tier": "HIGH",
  "status_color": "RED",
  "subscores": {
    "breach_subscore": 70,
    "access_subscore": 90,
    "compliance_subscore": 60,
    "financial_subscore": 50
  },
  "weights": { "breach": 0.40, "access": 0.25, "compliance": 0.20, "financial": 0.15 },
  "anomaly_types": ["HIGH_RISK_SCORE", "EXPIRED_CERTIFICATION"],
  "rationale": "Acme Cloud Storage scores HIGH primarily due to a SOC 2 Type II certification that expired four months ago combined with active PII access. No breach activity has been detected in the past 12 months, which keeps the score below CRITICAL.",
  "triggered_by": "extraction_complete",
  "previous_score": { "composite_score": 71, "tier": "MEDIUM", "status_color": "YELLOW", "computed_at": "2026-03-01T00:00:00Z" }
}
```
`triggered_by` tells the UI *why* this score exists (`manual | extraction_complete | breach_detected | cert_status_change | financial_signal_change | scheduled_sweep`) — useful for the risk-history timeline (§3 "Trend") to explain what changed, not just that it did.

### `POST /vendors/{vendor_id}/rescore`
Force an immediate recompute (e.g., user just updated a cert). Returns the same shape as `GET .../score`. Use sparingly — scoring also auto-triggers on relevant `PATCH`/extraction events.

### `GET /portfolio/score-distribution`
Backs the portfolio summary widget / pie-or-bar chart — Red/Yellow/Green at a glance, the Option A "portfolio view" requirement.
```json
{
  "by_tier": { "CRITICAL": 12, "HIGH": 48, "MEDIUM": 110, "LOW": 90, "CLEAR": 152 },
  "by_status_color": { "RED": 60, "YELLOW": 200, "GREEN": 152 },
  "total_vendors": 412,
  "as_of": "2026-06-20T06:00:00Z"
}
```

### `GET /portfolio/score-trend?range=90d`
Backs the trend-over-time line chart. `range`: `30d | 90d | 1y`.
```json
{
  "points": [
    { "date": "2026-05-01", "by_tier": { "CRITICAL": 9, "HIGH": 41, "MEDIUM": 105, "LOW": 95, "CLEAR": 162 } }
  ]
}
```

## 4. Extraction & Evidence Ingestion (all Option A document/source types)

### `POST /vendors/{vendor_id}/extract`
Multipart upload (PDF or pasted text via `text` field) **or** JSON body with `text`. Accepts a `document_type` field so the extraction prompt template matches the source:

| `document_type` | Use |
|---|---|
| `contract` | Data access permissions, SLA terms, compliance requirements |
| `security_assessment` | Self-reported Q&A-style assessment/questionnaire |
| `audit_report` | SOC 2 Type I/II, ISO 27001, PCI-DSS report text |

Kicks off async extraction job.

**Response 202:**
```json
{ "extraction_job_id": "uuid", "status": "pending", "document_type": "audit_report" }
```

### `GET /extraction-jobs/{job_id}`
Poll for result (frontend should poll every 2–3s, or use SSE if implemented — see Stretch Goals).

```json
{
  "id": "uuid",
  "vendor_id": "uuid",
  "document_type": "contract",
  "status": "done",
  "structured_output": {
    "data_access": { "pii": true, "financial": false, "systems": ["customer_db"] },
    "compliance_claims": [{ "type": "SOC2_TYPE2", "claimed_status": "current", "claimed_expiry": "2026-06-01" }],
    "sla_terms": { "uptime_pct": 99.9, "breach_notification_hours": 72 }
  },
  "conflicts": [
    {
      "field": "certifications.SOC2_TYPE2.status",
      "claimed": "current",
      "actual_on_record": "expired",
      "note": "Vendor's contract text claims current SOC 2, but our records show it expired 2025-06-01. Flagged for manual review — not auto-resolved."
    }
  ],
  "completed_at": "2026-06-20T07:00:00Z"
}
```

**UI guidance:** any non-empty `conflicts` array should render as a distinct warning state (not just folded into the normal extraction result) — this is a deliberate product decision, see `NOVELTY.md` §2.

### `GET /vendors/{vendor_id}/evidence`
Lists raw `EvidenceSignal` records for a vendor — breach-DB hits, public-records updates, status-API drift — separate from document-driven `ExtractionJob`s. Useful for an "evidence trail" panel on the drill-down view.

```json
{
  "items": [
    {
      "id": "uuid",
      "source": "breach_db",
      "signal_type": "new_breach",
      "received_at": "2026-06-15T00:00:00Z",
      "payload": { "severity": "HIGH", "description": "Unauthorized access to staging bucket" },
      "consumed_by_score_id": "uuid"
    },
    {
      "id": "uuid",
      "source": "status_api",
      "signal_type": "cert_status_change",
      "received_at": "2026-06-10T00:00:00Z",
      "payload": { "cert_type": "SOC2_TYPE2", "live_status": "current", "stored_status": "expired", "matched": false },
      "consumed_by_score_id": null
    }
  ]
}
```
A `matched: false` payload on a `status_api` signal means the live check disagreed with our records — surface this the same way as an extraction `conflict`.

## 5. Alerts

### `GET /alerts`
Query params: `status` (`open|acknowledged|resolved`, default `open`), `severity`, `vendor_id`, `type`, pagination.

`type` values: `CERT_EXPIRING | CONTRACT_EXPIRING | ASSESSMENT_OVERDUE | NEW_BREACH | SCORE_TIER_CHANGED`.

```json
{
  "items": [
    {
      "id": "uuid",
      "vendor_id": "uuid",
      "vendor_name": "Acme Cloud Storage",
      "type": "CERT_EXPIRING",
      "severity": "HIGH",
      "message": "SOC2_TYPE2 certification expires in 25 days",
      "created_at": "2026-06-18T00:00:00Z",
      "acknowledged_at": null,
      "resolved_at": null
    },
    {
      "id": "uuid",
      "vendor_id": "uuid",
      "vendor_name": "Acme Cloud Storage",
      "type": "SCORE_TIER_CHANGED",
      "severity": "HIGH",
      "message": "Risk tier changed MEDIUM → HIGH following a new breach detection",
      "created_at": "2026-06-15T00:05:00Z",
      "acknowledged_at": null,
      "resolved_at": null
    }
  ],
  "page": 1, "page_size": 25, "total_items": 37, "total_pages": 2
}
```

### `POST /alerts/{alert_id}/acknowledge`
### `POST /alerts/{alert_id}/resolve`
Both return the updated alert object. No body required for acknowledge; `resolve` accepts an optional `{ "resolution_note": string }`.

### `GET /alerts/summary`
Badge/counter widget for nav bar.
```json
{ "open_critical": 3, "open_high": 12, "open_total": 37 }
```

## 6. Reports

### `GET /vendors/{vendor_id}/report?format=pdf|markdown`
Returns either a `application/pdf` binary or `text/markdown` text, framed against GDPR Art. 28/33, NIST SP 800-53 SA-9, SOX 404 as applicable. Frontend should offer a direct download link, not render PDF inline unless a viewer component is already in place.

### `GET /portfolio/report?format=pdf|markdown`
Same as above, full-portfolio audit report (risk-by-category, trending, recommendations).

### `GET /vendors/export.csv`
Same filter params as `GET /vendors`; returns `text/csv` for the "export for audit" button.

## 7. Evaluation (internal/demo use — optional to surface in UI)

### `GET /admin/evaluation`
Returns the latest run of `scripts/evaluate.py` for a "model quality" panel if the team wants to show judges live accuracy numbers.
```json
{
  "run_at": "2026-06-20T05:00:00Z",
  "overall_accuracy": 0.83,
  "by_tier": {
    "CRITICAL": { "precision": 0.78, "recall": 0.95, "f1": 0.86 },
    "HIGH": { "precision": 0.74, "recall": 0.88, "f1": 0.80 }
  }
}
```

## 8. Auth (minimal, hackathon-scope)

- `POST /auth/login` → `{ "access_token": "...", "role": "ciso|procurement|auditor" }`
- Token sent as `Authorization: Bearer <token>` on subsequent requests
- Role is informational for the frontend (e.g., hide "delete vendor" for `auditor` role) — backend does not yet enforce fine-grained permissions per role; treat as UI-level gating only for the hackathon demo

## 9. WebSocket / Polling for Live Demo Moments

For the scripted "live breach arrives mid-demo" moment (see `NOVELTY.md` §6):
- **MVP approach (recommended):** frontend polls `GET /alerts/summary` and `GET /portfolio/score-distribution` every 5s while the dashboard is open — simplest to build reliably under hackathon time pressure
- **Stretch goal:** `WS /ws/alerts` pushes new alert events in real time, payload identical to a single item from `GET /alerts`

## 10. Sample End-to-End Flow (for frontend dev reference)

1. Dashboard loads → `GET /portfolio/score-distribution` (Red/Yellow/Green counts) + `GET /alerts/summary` + `GET /vendors?sort=score_desc&page=1`
2. User clicks a vendor row → `GET /vendors/{id}` (includes `current_score`) + `GET /vendors/{id}/score` for full breakdown + `GET /vendors/{id}/evidence` for the non-document signal trail
3. User uploads a new contract PDF on that vendor → `POST /vendors/{id}/extract` (`document_type=contract`) → poll `GET /extraction-jobs/{job_id}` until `status: done` → if `conflicts` non-empty, show warning banner → refresh `GET /vendors/{id}/score` (auto-rescored server-side, `triggered_by: extraction_complete`)
4. User clicks "Generate Audit Report" → `GET /vendors/{id}/report?format=pdf` → trigger browser download
5. User acknowledges an alert from the feed → `POST /alerts/{alert_id}/acknowledge` → optimistically remove from "open" list

## 11. Things the Frontend Should NOT Assume

- Scores can change between page loads without a user action (background monitoring sweeps run independently) — always treat `current_score`/`anomaly_types` as potentially stale after a few minutes and prefer refetching over long-lived local cache
- `composite_score` is 0–100 but **tier is the primary signal to render**, not the raw number — UI should lead with tier (color/badge), score as secondary detail
- `conflicts` in extraction results are never auto-resolved by the backend — if the UI doesn't surface them, that information is effectively lost to the user
- `EvidenceSignal` entries (from breach DB, public records, status API) are a separate trail from `ExtractionJob` entries (from document uploads) — both feed the same vendor, but the drill-down view should probably show both, not just one

## 12. Why This Matches Option A

| Endpoint(s) | Option A requirement |
|---|---|
| `POST /vendors/{id}/extract` (`document_type=contract`) | "Extract contract obligations using NLP (identify data access permissions)" |
| `POST /vendors/{id}/extract` (`document_type=audit_report`) | "Summarize vendor compliance... parse SOC 2, ISO 27001 reports into structured format" |
| `GET /vendors/{id}/evidence` (`source=breach_db`) | "Breach databases (check if vendor is breached)" + "New breach detection" |
| `GET /vendors/{id}/evidence` (`source=public_records`) | "Public records (financial health, regulatory issues)" |
| `GET /vendors/{id}/evidence` (`source=status_api`) | "Third-party integrations (vendor's own API for SOC 2 status, etc.)" |
| `rationale` field on `GET /vendors/{id}/score` | "Generate risk narratives" |
| `subscores` + `weights` on `GET /vendors/{id}/score` | "Risk scoring engine: Combine breach history + data access scope + compliance maturity + financial stability" |
| `triggered_by` on score, `POST /vendors/{id}/rescore` | "Dynamically recalculate when new info appears" |
| `status_color` (RED/YELLOW/GREEN) everywhere | "Output: Red/Yellow/Green with change alerts" |
| `SCORE_TIER_CHANGED` alert type | "...with change alerts" |
| `GET /vendors` + `GET /portfolio/score-distribution` | "Portfolio view (100 vendors, see who's risky at a glance)" |
| `GET /alerts?type=CERT_EXPIRING` | "Certification tracking (when SOC 2 expires?)" |
