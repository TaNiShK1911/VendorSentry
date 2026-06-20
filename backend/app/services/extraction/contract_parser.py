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
    document_text: str,
    db: Session,
    document_type: str = "contract",
) -> ExtractionJob:
    """
    Run LLM extraction on a vendor document (contract / assessment / audit report).

    Steps:
    1. Create a pending ExtractionJob row immediately (so the API can return 202).
    2. Build prompt with existing vendor context for conflict detection.
    3. Call the LLM.
    4. Parse JSON output.
    5. Run conflict checker against stored DB fields.
    6. Persist structured_output + flagged_conflicts on the job row.

    Args:
        vendor:        The Vendor ORM object (with relationships loaded).
        document_text: Raw text content of the uploaded document.
        db:            SQLAlchemy session.
        document_type: "contract" | "security_assessment" | "audit_report".

    Returns:
        ExtractionJob ORM object (persisted, status="done" or "failed").
    """
    # Step 1 — Create the job row immediately so the caller gets a job_id to poll
    job = ExtractionJob(
        id=str(uuid.uuid4()),
        vendor_id=vendor.id,
        source_type=_map_document_type(document_type),
        raw_text=document_text[:50_000],  # Truncate very large docs for storage
        status="processing",
    )
    db.add(job)
    db.flush()  # get the id without committing

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

        logger.info(
            "ExtractionJob %s completed: vendor=%s type=%s conflicts=%d",
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
