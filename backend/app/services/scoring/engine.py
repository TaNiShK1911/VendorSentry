"""
Risk Scoring Engine — the deterministic core of VendorSentry.

Composite formula (IMPLEMENTATION_PLAN.md §4):
    composite = 0.40 * breach_subscore
              + 0.25 * access_subscore
              + 0.20 * compliance_subscore
              + 0.15 * financial_subscore

ARCHITECTURAL RULES (AGENT.md Hard Rules):
1. The LLM NEVER writes composite_score, tier, or status_color.
   Those fields are always produced by this module alone.
2. ground_truth (vendor_labels.csv) is never imported here.
3. This module must stay unit-testable with plain Python — no DB
   session required for the pure compute functions.

Public API (for Dev B to call from endpoints):
    score_vendor(vendor_data) -> VendorScoreResult
    score_vendor_from_db(vendor_id, db) -> VendorScore (ORM object, saved)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models.vendor import Vendor
from app.models.vendor_score import VendorScore
from app.models.breach import BreachEvent
from app.models.certification import Certification
from app.models.data_access import DataAccessScope
from app.core.config import get_settings
from app.services.scoring.subscore_breach import compute_breach_subscore
from app.services.scoring.subscore_access import compute_access_subscore
from app.services.scoring.subscore_compliance import compute_compliance_subscore
from app.services.scoring.subscore_financial import compute_financial_subscore
from app.services.scoring.tiering import determine_tier


settings = get_settings()


# --------------------------------------------------------------------------- #
# Intermediate data container — decouples pure compute from ORM
# --------------------------------------------------------------------------- #

@dataclass
class VendorScoreResult:
    """
    Plain-Python result of a scoring computation.
    Used by both the DB-backed path and unit tests (no ORM needed).
    """
    vendor_id: str
    breach_subscore: float
    access_subscore: float
    compliance_subscore: float
    financial_subscore: float
    composite_score: float
    tier: str
    status_color: str
    anomaly_types: list[str]
    triggered_by: str
    rationale: Optional[str] = None   # filled in by narrative.py after scoring


# --------------------------------------------------------------------------- #
# Pure compute functions (unit-testable, no DB, no LLM)
# --------------------------------------------------------------------------- #

def compute_composite(
    breach_subscore: float,
    access_subscore: float,
    compliance_subscore: float,
    financial_subscore: float,
) -> float:
    """
    Apply the weighted formula and return a score in [0, 100].

    Weights come from settings so they can be tuned via .env without
    a code change. They must sum to 1.0 (validated in Settings).
    """
    composite = (
        settings.weight_breach     * breach_subscore
        + settings.weight_access   * access_subscore
        + settings.weight_compliance * compliance_subscore
        + settings.weight_financial  * financial_subscore
    )
    return round(min(100.0, max(0.0, composite)), 2)


def score_vendor(
    vendor: Vendor,
    breaches: Sequence[BreachEvent],
    certs: Sequence[Certification],
    scope: Optional[DataAccessScope],
    triggered_by: str = "manual",
) -> VendorScoreResult:
    """
    Pure scoring function — takes ORM objects but makes no DB calls.

    Args:
        vendor:       The Vendor ORM object (read-only).
        breaches:     All BreachEvent rows for this vendor.
        certs:        All Certification rows for this vendor.
        scope:        DataAccessScope for this vendor (may be None).
        triggered_by: What caused this scoring event.

    Returns:
        VendorScoreResult — a plain dataclass, not yet persisted.

    NOTE: rationale is None here. Call narrative.generate_rationale()
          AFTER this function returns, then attach the result before saving.
    """
    breach_sub   = compute_breach_subscore(breaches, vendor.under_investigation)
    access_sub   = compute_access_subscore(scope)
    compliance_sub = compute_compliance_subscore(certs, vendor.last_assessed_at)
    financial_sub  = compute_financial_subscore(vendor.financial_health_signal)

    composite = compute_composite(breach_sub, access_sub, compliance_sub, financial_sub)

    tier, anomaly_types, status_color = determine_tier(
        composite_score=composite,
        vendor=vendor,
        breaches=breaches,
        certs=certs,
        scope=scope,
    )

    return VendorScoreResult(
        vendor_id=vendor.id,
        breach_subscore=breach_sub,
        access_subscore=access_sub,
        compliance_subscore=compliance_sub,
        financial_subscore=financial_sub,
        composite_score=composite,
        tier=tier,
        status_color=status_color,
        anomaly_types=anomaly_types,
        triggered_by=triggered_by,
        rationale=None,
    )


# --------------------------------------------------------------------------- #
# Stub for Dev B — replace with real implementation after scoring engine is done
# Dev B can call this from hour 1 to build endpoints before the real engine lands
# --------------------------------------------------------------------------- #

def score_vendor_stub(vendor: Vendor) -> VendorScoreResult:
    """
    STUB — returns a fixed mock so Dev B can build endpoints immediately.
    Replace: this function is replaced by score_vendor_from_db() at Hour 14.
    """
    return VendorScoreResult(
        vendor_id=vendor.id,
        breach_subscore=0.0,
        access_subscore=20.0,
        compliance_subscore=100.0,
        financial_subscore=40.0,
        composite_score=50.0,
        tier="MEDIUM",
        status_color="YELLOW",
        anomaly_types=[],
        triggered_by="manual",
        rationale="Stub — real scoring not yet computed.",
    )


# --------------------------------------------------------------------------- #
# DB-backed scoring path (loads data, calls score_vendor, persists result)
# --------------------------------------------------------------------------- #

def score_vendor_from_db(
    vendor_id: str,
    db: Session,
    triggered_by: str = "manual",
    previous_score_id: Optional[str] = None,
    rationale: Optional[str] = None,
) -> VendorScore:
    """
    Load vendor data from DB, compute score, persist and return the new VendorScore row.

    This is the function Dev B calls from:
      - POST /vendors/{id}/rescore
      - After any PATCH /vendors/{id}
      - After ExtractionJob completion
      - From Celery monitoring sweep tasks

    Args:
        vendor_id:        UUID string of the vendor to score.
        db:               SQLAlchemy session (injected by FastAPI or Celery).
        triggered_by:     Reason for this scoring event.
        previous_score_id: ID of the VendorScore row being superseded.
        rationale:        LLM-generated narrative (attached AFTER scoring).

    Returns:
        VendorScore ORM object (already added to session, not yet committed).

    Raises:
        ValueError: if vendor_id is not found.
    """
    # Load vendor with all related data in one query batch
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise ValueError(f"Vendor {vendor_id!r} not found")

    breaches = vendor.breach_history
    certs    = vendor.certifications
    scope    = vendor.data_access_scope

    # Determine the previous score id if not provided
    if previous_score_id is None and vendor.scores:
        previous_score_id = vendor.scores[0].id  # most recent (ordered desc)

    # Run pure scoring
    result = score_vendor(vendor, breaches, certs, scope, triggered_by)

    # Build the ORM row
    score_row = VendorScore(
        id=str(uuid.uuid4()),
        vendor_id=vendor_id,
        computed_at=datetime.utcnow(),
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        composite_score=result.composite_score,
        tier=result.tier,
        status_color=result.status_color,
        anomaly_types=result.anomaly_types,
        triggered_by=result.triggered_by,
        previous_score_id=previous_score_id,
        rationale=rationale,  # May be None; narrative.py fills this in async
    )

    db.add(score_row)
    return score_row
