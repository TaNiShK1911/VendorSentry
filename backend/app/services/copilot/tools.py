"""
Copilot tool manifest and execution layer.

Each tool maps to a direct service-layer or DB query — never an HTTP call.
Tools return plain dicts/lists so they can be JSON-serialised for the LLM.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Alert, Vendor, VendorScore, DataAccessScope, EvidenceSignal
from app.models.breach import BreachEvent
from app.services.scoring.engine import get_latest_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool Manifest — passed to Groq as tool definitions
# ---------------------------------------------------------------------------

TOOL_MANIFEST = [
    {
        "type": "function",
        "function": {
            "name": "list_alerts",
            "description": "List open alerts. Filters: alert_type (NEW_BREACH, CERT_EXPIRING, CONTRACT_EXPIRING, ASSESSMENT_OVERDUE, SCORE_TIER_CHANGED), severity (CRITICAL, HIGH, MEDIUM, LOW), vendor_id (UUID string), acknowledged (boolean), created_after (ISO 8601 string). Returns up to 30 results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alert_type":   {"type": "string",  "description": "One of: NEW_BREACH, CERT_EXPIRING, CONTRACT_EXPIRING, ASSESSMENT_OVERDUE, SCORE_TIER_CHANGED"},
                    "severity":     {"type": "string",  "description": "One of: CRITICAL, HIGH, MEDIUM, LOW"},
                    "vendor_id":    {"type": "string",  "description": "Vendor UUID to filter by"},
                    "acknowledged": {"type": "boolean", "description": "true=acknowledged only, false=unacknowledged only"},
                    "created_after":{"type": "string",  "description": "ISO 8601 UTC timestamp cutoff, e.g. 2026-06-19T00:00:00Z"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_vendors",
            "description": "List vendors in the portfolio. Optional filters: risk_tier (CRITICAL, HIGH, MEDIUM, LOW, CLEAR), search (name substring), sort_by (score_desc, score_asc, name_asc, name_desc). Returns up to 20 results sorted by risk score by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "risk_tier": {"type": "string", "description": "Filter to vendors in this tier: CRITICAL, HIGH, MEDIUM, LOW, or CLEAR"},
                    "search":    {"type": "string", "description": "Substring to search in vendor name"},
                    "sort_by":   {"type": "string", "description": "Sort order: score_desc, score_asc, name_asc, or name_desc"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor_detail",
            "description": "Get full profile for a single vendor: score breakdown, certifications, breach history, contract dates, data access scope.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {"type": "string", "description": "The vendor UUID"}
                },
                "required": ["vendor_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_distribution",
            "description": "Get overall portfolio risk distribution: count by tier (CRITICAL/HIGH/MEDIUM/LOW/CLEAR) and status color (RED/YELLOW/GREEN), plus average composite score.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts_summary",
            "description": "Get total count of open alerts broken down by severity and type. Use for dashboard-level health questions.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor_breaches",
            "description": "Get all known breach events for a specific vendor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {"type": "string", "description": "The vendor UUID"}
                },
                "required": ["vendor_id"]
            }
        }
    }
]


# ---------------------------------------------------------------------------
# Tool execution layer
# ---------------------------------------------------------------------------

def _fmt_dt(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def execute_tool(tool_name: str, tool_input: dict, db: Session) -> dict[str, Any]:
    """
    Execute a named tool against the live DB.

    Returns a plain dict that is JSON-serialisable.
    Raises ValueError for unknown tools.
    """
    try:
        if tool_name == "list_alerts":
            return _list_alerts(tool_input, db)
        elif tool_name == "list_vendors":
            return _list_vendors(tool_input, db)
        elif tool_name == "get_vendor_detail":
            return _get_vendor_detail(tool_input, db)
        elif tool_name == "get_portfolio_distribution":
            return _get_portfolio_distribution(db)
        elif tool_name == "get_alerts_summary":
            return _get_alerts_summary(db)
        elif tool_name == "get_vendor_breaches":
            return _get_vendor_breaches(tool_input, db)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as exc:
        logger.exception("Tool %s failed: %s", tool_name, exc)
        return {"error": str(exc), "tool": tool_name}


# ---------------------------------------------------------------------------
# Individual tool implementations
# ---------------------------------------------------------------------------

def _list_alerts(params: dict, db: Session) -> dict:
    query = db.query(Alert)
    query = query.filter(Alert.resolved_at.is_(None))

    if at := params.get("alert_type"):
        query = query.filter(Alert.type == at)

    if sev := params.get("severity"):
        query = query.filter(Alert.severity == sev.upper())

    if vid := params.get("vendor_id"):
        query = query.filter(Alert.vendor_id == vid)

    if params.get("acknowledged") is True:
        query = query.filter(Alert.acknowledged_at.isnot(None))
    elif params.get("acknowledged") is False:
        query = query.filter(Alert.acknowledged_at.is_(None))

    if ca := params.get("created_after"):
        try:
            cutoff = datetime.fromisoformat(ca.replace("Z", "+00:00"))
            if cutoff.tzinfo:
                cutoff = cutoff.replace(tzinfo=None)  # DB stores UTC naive
            query = query.filter(Alert.created_at >= cutoff)
        except ValueError:
            pass

    limit = min(int(params.get("limit", 30)), 100)
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

    items = []
    for alert in alerts:
        vendor = db.query(Vendor).filter(Vendor.id == alert.vendor_id).first()
        items.append({
            "id": str(alert.id),
            "vendor_id": str(alert.vendor_id),
            "vendor_name": vendor.name if vendor else "Unknown",
            "alert_type": str(alert.type.value) if hasattr(alert.type, "value") else str(alert.type),
            "severity": str(alert.severity.value) if hasattr(alert.severity, "value") else str(alert.severity),
            "message": alert.message,
            "acknowledged": alert.acknowledged_at is not None,
            "created_at": _fmt_dt(alert.created_at),
        })

    return {"count": len(items), "alerts": items}


def _list_vendors(params: dict, db: Session) -> dict:
    query = db.query(Vendor).filter(Vendor.archived_at.is_(None))

    if search := params.get("search"):
        query = query.filter(Vendor.name.ilike(f"%{search}%"))

    vendors = query.all()

    # Get scores for all vendors
    items = []
    for vendor in vendors:
        score = get_latest_score(str(vendor.id), db)
        scope = db.query(DataAccessScope).filter(DataAccessScope.vendor_id == vendor.id).first()
        alert_count = db.query(Alert).filter(
            Alert.vendor_id == vendor.id,
            Alert.resolved_at.is_(None)
        ).count()

        tier = score.tier if score else "CLEAR"

        # Apply risk_tier filter post-fetch (since tier comes from scores)
        if rt := params.get("risk_tier"):
            if tier.upper() != rt.upper():
                continue

        items.append({
            "id": str(vendor.id),
            "name": vendor.name,
            "vendor_type": vendor.vendor_type,
            "website_domain": vendor.website_domain,
            "annual_spend": float(vendor.annual_spend) if vendor.annual_spend else 0,
            "contract_end": str(vendor.contract_end) if vendor.contract_end else None,
            "has_pii_access": scope.pii_access if scope else False,
            "has_financial_access": scope.financial_access if scope else False,
            "composite_score": score.composite_score if score else 0.0,
            "risk_tier": tier,
            "status_color": score.status_color if score else "GREEN",
            "active_alerts": alert_count,
        })

    # Sort
    sort = params.get("sort_by", "score_desc")
    reverse = sort.endswith("_desc")
    key = "composite_score" if "score" in sort else "name"
    items.sort(key=lambda x: x.get(key, 0), reverse=reverse)

    # Cap at 20 results — hardcoded, not from LLM (avoids integer type errors)
    items = items[:20]

    return {"count": len(items), "vendors": items}


def _get_vendor_detail(params: dict, db: Session) -> dict:
    vid = params.get("vendor_id")
    vendor = db.query(Vendor).filter(Vendor.id == vid).first()
    if not vendor:
        return {"error": f"Vendor {vid} not found"}

    score = get_latest_score(str(vendor.id), db)
    scope = db.query(DataAccessScope).filter(DataAccessScope.vendor_id == vendor.id).first()
    alert_count = db.query(Alert).filter(
        Alert.vendor_id == vendor.id, Alert.resolved_at.is_(None)
    ).count()
    breaches = db.query(BreachEvent).filter(BreachEvent.vendor_id == vendor.id).all()

    from app.models import Certification
    certs = db.query(Certification).filter(Certification.vendor_id == vendor.id).all()

    return {
        "id": str(vendor.id),
        "name": vendor.name,
        "vendor_type": vendor.vendor_type,
        "website_domain": vendor.website_domain,
        "annual_spend": float(vendor.annual_spend) if vendor.annual_spend else 0,
        "contract_start": str(vendor.contract_start) if vendor.contract_start else None,
        "contract_end": str(vendor.contract_end) if vendor.contract_end else None,
        "financial_health_signal": vendor.financial_health_signal,
        "under_investigation": vendor.under_investigation,
        "has_pii_access": scope.pii_access if scope else False,
        "has_financial_access": scope.financial_access if scope else False,
        "systems_access": scope.systems if scope else [],
        "active_alerts": alert_count,
        "breach_count": len(breaches),
        "recent_breaches": [
            {
                "date": str(b.breach_date),
                "severity": str(b.severity),
                "description": b.description,
                "resolved": b.resolved,
            }
            for b in breaches[:5]
        ],
        "certifications": [
            {
                "cert_type": c.cert_type,
                "status": c.status,
                "expiry_date": str(c.expiry_date) if c.expiry_date else None,
            }
            for c in certs
        ],
        "current_score": {
            "composite_score": score.composite_score,
            "risk_tier": score.tier,
            "status_color": score.status_color,
            "breach_subscore": score.breach_subscore,
            "access_subscore": score.access_subscore,
            "compliance_subscore": score.compliance_subscore,
            "financial_subscore": score.financial_subscore,
            "anomaly_types": score.anomaly_types or [],
            "rationale": score.rationale,
            "computed_at": _fmt_dt(score.computed_at),
        } if score else None,
    }


def _get_portfolio_distribution(db: Session) -> dict:
    vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
    by_tier = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "CLEAR": 0}
    by_color = {"RED": 0, "YELLOW": 0, "GREEN": 0}
    scores = []

    for vendor in vendors:
        score = get_latest_score(str(vendor.id), db)
        if score:
            tier = str(score.tier)
            color = str(score.status_color)
            by_tier[tier] = by_tier.get(tier, 0) + 1
            by_color[color] = by_color.get(color, 0) + 1
            scores.append(score.composite_score)
        else:
            by_tier["CLEAR"] += 1
            by_color["GREEN"] += 1
            scores.append(0.0)

    avg = round(sum(scores) / len(scores), 2) if scores else 0.0
    return {
        "total_vendors": len(vendors),
        "by_tier": by_tier,
        "by_status_color": by_color,
        "avg_composite_score": avg,
        "highest_score": max(scores) if scores else 0.0,
        "lowest_score": min(scores) if scores else 0.0,
    }


def _get_alerts_summary(db: Session) -> dict:
    def count(severity=None, alert_type=None):
        q = db.query(Alert).filter(Alert.resolved_at.is_(None))
        if severity:
            q = q.filter(Alert.severity == severity)
        if alert_type:
            q = q.filter(Alert.type == alert_type)
        return q.count()

    return {
        "total_open": count(),
        "by_severity": {
            "critical": count(severity="CRITICAL"),
            "high": count(severity="HIGH"),
            "medium": count(severity="MEDIUM"),
            "low": count(severity="LOW"),
        },
        "by_type": {
            "NEW_BREACH": count(alert_type="NEW_BREACH"),
            "CERT_EXPIRING": count(alert_type="CERT_EXPIRING"),
            "CONTRACT_EXPIRING": count(alert_type="CONTRACT_EXPIRING"),
            "ASSESSMENT_OVERDUE": count(alert_type="ASSESSMENT_OVERDUE"),
            "SCORE_TIER_CHANGED": count(alert_type="SCORE_TIER_CHANGED"),
        }
    }


def _get_vendor_breaches(params: dict, db: Session) -> dict:
    vid = params.get("vendor_id")
    vendor = db.query(Vendor).filter(Vendor.id == vid).first()
    if not vendor:
        return {"error": f"Vendor {vid} not found"}

    breaches = db.query(BreachEvent).filter(
        BreachEvent.vendor_id == vid
    ).order_by(BreachEvent.breach_date.desc()).all()

    return {
        "vendor_name": vendor.name,
        "count": len(breaches),
        "breaches": [
            {
                "id": str(b.id),
                "date": str(b.breach_date),
                "severity": str(b.severity),
                "source": str(b.source) if hasattr(b.source, "value") else b.source,
                "description": b.description,
                "resolved": b.resolved,
                "created_at": _fmt_dt(b.created_at),
            }
            for b in breaches
        ]
    }
