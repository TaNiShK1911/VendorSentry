"""
Contract parser — LLM-powered extraction from vendor contract documents.

Extracts: data access permissions, SLA terms, compliance requirements.
Implements IMPLEMENTATION_PLAN.md §3.2 and Option A's
"Extract contract obligations using NLP (identify data access permissions)" bullet.

ARCHITECTURAL RULES:
- Never writes composite_score, tier, or status_color.
- Always runs conflict_checker after extraction.
- Conflicts are stored on the ExtractionJob row; not silently resolved.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.extraction_job import ExtractionJob
from app.models.vendor import Vendor
from app.services.extraction.llm_client import get_llm_client
from app.services.extraction.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.extraction.conflict_checker import check_conflicts

logger = logging.getLogger(__name__)


def _build_existing_vendor_data(vendor: Vendor) -> dict:
    """Summarise stored vendor fields for LLM conflict-detection context."""
    certs = [
        {
            "type": c.cert_type,
            "status": c.status,
            "expiry_date": str(c.expiry_date) if c.expiry_date else None,
        }
        for c in (vendor.certifications or [])
    ]
    scope = vendor.data_access_scope
    return {
        "name": vendor.name,
        "certifications": certs,
        "data_access": {
            "pii": scope.pii_access if scope else None,
            "financial": scope.financial_access if scope else None,
        } if scope else {},
    }


def extract_contract(
    vendor: Vendor,
    job: ExtractionJob,
    document_text: str,
    db: Session,
    document_type: str = "contract",
) -> ExtractionJob:
    """
    Run LLM extraction on a vendor document (contract / assessment / audit report).

    Steps:
    1. Build prompt with existing vendor context for conflict detection.
    2. Call the LLM.
    3. Parse JSON output.
    4. Run conflict checker against stored DB fields.
    5. Persist structured_output + flagged_conflicts on the job row.

    Args:
        vendor:        The Vendor ORM object (with relationships loaded).
        job:           The pending ExtractionJob row already persisted.
        document_text: Raw text content of the uploaded document.
        db:            SQLAlchemy session.
        document_type: "contract" | "security_assessment" | "audit_report".

    Returns:
        ExtractionJob ORM object (persisted, status="done" or "failed").
    """

    try:
        # Step 2 — Build prompt
        existing_data = _build_existing_vendor_data(vendor)
        # Truncate text to fit comfortably within Groq's strict 8000 TPM limits
        user_prompt = build_user_prompt(document_type, document_text[:5000], existing_data)

        # Step 3 — Call LLM
        client = get_llm_client()
        raw_output = client.complete_json(SYSTEM_PROMPT, user_prompt)

        # Step 4 — Validate: ensure output has no forbidden fields
        _assert_no_score_fields(raw_output, job.id)

        # Step 5 — Conflict check against DB state
        conflicts = check_conflicts(
            extracted=raw_output,
            existing_certs=vendor.certifications or [],
            existing_scope=vendor.data_access_scope,
        )
        # Merge any conflicts the LLM itself reported with what we detected
        llm_conflicts = raw_output.pop("conflicts", [])
        all_conflicts = llm_conflicts + [c.model_dump() for c in conflicts]

        # Step 6 — Persist results
        job.structured_output = raw_output
        job.flagged_conflicts = all_conflicts
        job.status = "done"
        job.completed_at = datetime.utcnow()

        # Step 7 — Merge extracted facts into vendor record.
        # When conflicts exist, we merge only the non-conflicting fields.
        conflicted_fields = {c.get("field", "") for c in all_conflicts}
        _merge_extracted_facts(vendor, raw_output, db, conflicted_fields)

        # Step 8 — Always rescore after extraction so dashboard/alerts update
        from app.services.scoring.engine import score_vendor_from_db
        from app.services.extraction.narrative import generate_rationale

        # Flush so the updated facts are saved before scoring
        db.flush()

        score = score_vendor_from_db(vendor.id, db, triggered_by="extraction_complete")

        rationale = generate_rationale(
            vendor_name=vendor.name,
            composite_score=score.composite_score,
            tier=score.tier,
            breach_subscore=score.breach_subscore,
            access_subscore=score.access_subscore,
            compliance_subscore=score.compliance_subscore,
            financial_subscore=score.financial_subscore,
            anomaly_types=score.anomaly_types
        )
        score.rationale = rationale
        db.flush()

        logger.info(
            "ExtractionJob %s completed: vendor=%s type=%s conflicts=%d — rescore triggered",
            job.id, vendor.id, document_type, len(all_conflicts),
        )

    except Exception as exc:
        logger.exception("ExtractionJob %s failed: %s", job.id, exc)
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()

    return job


def _map_document_type(document_type: str) -> str:
    """Map API document_type string to ExtractionJob.source_type enum value."""
    mapping = {
        "contract": "contract_pdf",
        "security_assessment": "security_assessment",
        "audit_report": "audit_report",
    }
    return mapping.get(document_type, "contract_pdf")


def _merge_extracted_facts(vendor: Vendor, extracted: dict, db: Session, conflicted_fields: set[str] | None = None) -> None:
    """Merge extracted facts into the vendor's record, taking the latest document as the source of truth."""
    from datetime import datetime

    # 1. Update data access scope (always overwrite with latest)
    if "data_access" in extracted:
        da = extracted["data_access"]
        if not vendor.data_access_scope:
            from app.models.data_access import DataAccessScope
            vendor.data_access_scope = DataAccessScope(vendor_id=vendor.id)
            db.add(vendor.data_access_scope)
            
        scope = vendor.data_access_scope
        if da.get("pii") is not None:
            val = str(da["pii"]).lower()
            scope.pii_access = val in ["true", "yes"]
        if da.get("financial") is not None:
            val = str(da["financial"]).lower()
            scope.financial_access = val in ["true", "yes"]
        if da.get("systems"):
            scope.systems = da["systems"]

    # 2. Update certifications (always overwrite/add based on latest)
    if "compliance_claims" in extracted:
        from app.models.certification import Certification
        for claim in extracted["compliance_claims"]:
            cert_type = claim.get("type", "")

            # Check if it already exists to update it
            existing = next((c for c in (vendor.certifications or []) if c.cert_type == cert_type), None)
            
            expiry_str = claim.get("claimed_expiry")
            expiry_date = None
            if expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if existing:
                existing.status = claim.get("claimed_status", existing.status)
                if expiry_date:
                    existing.expiry_date = expiry_date
            else:
                new_cert = Certification(
                    vendor_id=vendor.id,
                    cert_type=cert_type,
                    status=claim.get("claimed_status", "Valid"),
                    expiry_date=expiry_date,
                    source="extraction"
                )
                db.add(new_cert)
                if not vendor.certifications:
                    vendor.certifications = []
                vendor.certifications.append(new_cert)


def _assert_no_score_fields(output: dict, job_id: str) -> None:
    """
    ARCHITECTURAL GUARD: raise if the LLM somehow included scoring fields.
    This enforces the hard rule that LLM output never sets risk scores.
    """
    forbidden = {"composite_score", "tier", "status_color", "risk_score"}
    found = forbidden & set(output.keys())
    if found:
        logger.error(
            "ExtractionJob %s: LLM output contained forbidden score fields %s — stripping them.",
            job_id, found,
        )
        for field in found:
            del output[field]
