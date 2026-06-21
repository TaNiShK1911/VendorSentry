"""
Breach database polling via HIBP (Have I Been Pwned) — Celery task.

Replaces the old mock random.random() < 0.01 generator with real breach
detection using HIBP's free public API.

Per IMPLEMENTATION_PLAN.md §5, on new breach detection:
    - Domain match (confidence 1.0): auto-creates BreachEvent + EvidenceSignal,
      triggers immediate rescore with rationale, fires NEW_BREACH alert.
    - Fuzzy name match (confidence < 1.0): creates EvidenceSignal for human
      review only — does NOT create BreachEvent, does NOT trigger rescore.

Dedup: before creating a BreachEvent, checks if one already exists for this
vendor + this specific HIBP breach (via BreachEvent.external_id). Without this,
every poll would re-flag the same historical breaches as new.
"""
from __future__ import annotations

import logging
from datetime import datetime, date

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Vendor, EvidenceSignal, BreachEvent
from app.services.alerts.generator import create_new_breach_alert
from app.services.scoring.engine import score_vendor_from_db
from app.services.extraction.narrative import generate_rationale
from app.services.monitoring.breach_sources.hibp_client import fetch_breach_catalog
from app.services.monitoring.breach_sources.matcher import match_vendor_to_breaches
from app.services.monitoring.breach_sources.severity import infer_severity

logger = logging.getLogger(__name__)


def breach_already_recorded(db, vendor_id: str, external_id: str) -> bool:
    """Check whether a BreachEvent already exists for this vendor + breach combo."""
    return (
        db.query(BreachEvent)
        .filter(
            BreachEvent.vendor_id == vendor_id,
            BreachEvent.external_id == external_id,
        )
        .first()
        is not None
    )


def _parse_breach_date(breach: dict) -> date | None:
    """Extract breach date from HIBP data, returning None if unparseable."""
    raw = breach.get("BreachDate")
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _create_breach_event_and_rescore(db, vendor: Vendor, match) -> None:
    """
    For a confirmed domain match: create BreachEvent + EvidenceSignal,
    trigger rescore with rationale, and fire an alert.

    This preserves the existing post-detection pipeline exactly as it was.
    """
    breach = match.breach
    severity = infer_severity(breach)
    breach_name = breach.get("Name", "Unknown")
    breach_title = breach.get("Title", breach_name)
    description = (
        f"HIBP breach detected: {breach_title} "
        f"({breach.get('PwnCount', 'unknown')} accounts affected)"
    )

    # Create evidence signal
    signal = EvidenceSignal(
        vendor_id=vendor.id,
        source="breach_db",
        signal_type="new_breach",
        payload={
            "hibp_name": breach_name,
            "hibp_title": breach_title,
            "pwn_count": breach.get("PwnCount"),
            "breach_date": breach.get("BreachDate"),
            "data_classes": breach.get("DataClasses", []),
            "domain": breach.get("Domain"),
            "is_verified": breach.get("IsVerified"),
            "is_sensitive": breach.get("IsSensitive"),
            "severity": severity,
            "match_type": match.match_type,
            "confidence": match.confidence,
        },
        received_at=datetime.utcnow(),
    )
    db.add(signal)

    # Create BreachEvent with external_id for dedup
    breach_event = BreachEvent(
        vendor_id=vendor.id,
        breach_date=_parse_breach_date(breach),
        severity=severity,
        source="hibp",
        description=description,
        external_id=breach_name,
        resolved=False,
    )
    db.add(breach_event)

    # Flush so IDs are assigned before scoring
    db.flush()

    # Trigger rescore via DB method
    score = score_vendor_from_db(vendor.id, db, triggered_by="breach_detected")

    # Generate rationale
    rationale = generate_rationale(
        vendor_name=vendor.name,
        composite_score=score.composite_score,
        tier=score.tier,
        breach_subscore=score.breach_subscore,
        access_subscore=score.access_subscore,
        compliance_subscore=score.compliance_subscore,
        financial_subscore=score.financial_subscore,
        anomaly_types=score.anomaly_types,
    )
    score.rationale = rationale

    # Link signal to score
    db.flush()
    signal.consumed_by_score_id = score.id

    # Create alert
    create_new_breach_alert(
        db,
        vendor.id,
        vendor.name,
        description,
    )


def _write_review_signal(db, vendor: Vendor, match) -> None:
    """
    For a fuzzy name match: create an EvidenceSignal for human review.
    Does NOT create a BreachEvent. Does NOT trigger rescore.
    """
    breach = match.breach
    signal = EvidenceSignal(
        vendor_id=vendor.id,
        source="breach_db",
        signal_type="fuzzy_breach_match",
        payload={
            "hibp_name": breach.get("Name"),
            "hibp_title": breach.get("Title"),
            "pwn_count": breach.get("PwnCount"),
            "breach_date": breach.get("BreachDate"),
            "data_classes": breach.get("DataClasses", []),
            "domain": breach.get("Domain"),
            "match_confidence": match.confidence,
            "match_type": match.match_type,
            "vendor_name": vendor.name,
            "note": "Fuzzy name match — requires human review before promoting to breach history",
        },
        received_at=datetime.utcnow(),
    )
    db.add(signal)


@celery_app.task(name="app.services.monitoring.breach_watcher.poll_breach_db")
def poll_breach_db():
    """
    Poll HIBP breach catalog for new breach signals affecting registered vendors.

    Uses conditional fetch (check /latestbreach first) to avoid hammering
    the full catalog endpoint. Domain matches auto-create BreachEvent +
    trigger rescore; fuzzy matches flag for human review only.
    """
    db = SessionLocal()
    try:
        catalog = fetch_breach_catalog()
        if not catalog:
            logger.info("No breach catalog available — skipping poll")
            return "Breach DB poll complete: no catalog available"

        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()

        domain_breaches_detected = 0
        fuzzy_flags_created = 0

        for vendor in vendors:
            matches = match_vendor_to_breaches(vendor, catalog)

            for match in matches:
                if match.match_type == "domain":
                    # Dedup: skip if we already recorded this breach for this vendor
                    breach_name = match.breach.get("Name", "")
                    if breach_already_recorded(db, vendor.id, breach_name):
                        continue
                    _create_breach_event_and_rescore(db, vendor, match)
                    domain_breaches_detected += 1
                else:
                    # Fuzzy match — flag for review, don't auto-apply
                    _write_review_signal(db, vendor, match)
                    fuzzy_flags_created += 1

        db.commit()
        return (
            f"Breach DB poll complete: {domain_breaches_detected} new breaches detected, "
            f"{fuzzy_flags_created} fuzzy matches flagged for review"
        )
    except Exception:
        logger.exception("poll_breach_db failed")
        db.rollback()
        return "Breach DB poll failed — see logs"
    finally:
        db.close()
