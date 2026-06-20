"""
Conflict checker — cross-validates LLM extraction output against stored structured fields.

ARCHITECTURAL RULE: Conflicts are NEVER auto-resolved.
Both the LLM-claimed value and the existing DB value are stored.
The disagreement itself is surfaced to the user as a warning.

This module implements the grounding post-check described in
IMPLEMENTATION_PLAN.md §3 "Common extraction contract":
    "any certification/date it states must be cross-checked against
    existing structured fields post-hoc — mismatches become a `conflicts`
    entry, not a silent overwrite."
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Sequence

from app.models.certification import Certification
from app.models.data_access import DataAccessScope
from app.schemas.extraction import ConflictRecord

logger = logging.getLogger(__name__)


def check_conflicts(
    extracted: dict,
    existing_certs: Sequence[Certification],
    existing_scope: DataAccessScope | None,
) -> list[ConflictRecord]:
    """
    Compare LLM-extracted structured output against DB-persisted vendor data.

    Returns a list of ConflictRecord objects for every disagreement found.
    Empty list means no conflicts detected.

    Args:
        extracted:       The parsed LLM output dict (StructuredExtractionOutput shape).
        existing_certs:  Current Certification rows from the DB.
        existing_scope:  Current DataAccessScope row from the DB (may be None).

    Returns:
        List of ConflictRecord (may be empty).
    """
    conflicts: list[ConflictRecord] = []

    # ── Check compliance claims ──────────────────────────────────────────────
    compliance_claims = extracted.get("compliance_claims") or []
    cert_map = {c.cert_type: c for c in existing_certs}

    for claim in compliance_claims:
        cert_type = claim.get("type")
        if not cert_type:
            continue

        existing = cert_map.get(cert_type)
        if existing is None:
            # Vendor claims a cert we have no record of — flag it
            conflicts.append(ConflictRecord(
                field=f"certifications.{cert_type}",
                claimed=claim.get("claimed_status", "unknown"),
                actual_on_record=None,
                note=(
                    f"Document claims {cert_type} certification "
                    f"(status: {claim.get('claimed_status', 'unknown')}), "
                    f"but no record exists in VendorSentry. "
                    f"Flagged for manual verification — not auto-created."
                ),
            ))
            continue

        # Status conflict
        claimed_status = claim.get("claimed_status")
        if claimed_status and claimed_status != existing.status:
            conflicts.append(ConflictRecord(
                field=f"certifications.{cert_type}.status",
                claimed=claimed_status,
                actual_on_record=existing.status,
                note=(
                    f"Document claims {cert_type} is '{claimed_status}', "
                    f"but VendorSentry records show status '{existing.status}'. "
                    f"Flagged for manual review — not auto-resolved."
                ),
            ))

        # Expiry date conflict
        claimed_expiry_str = claim.get("claimed_expiry")
        if claimed_expiry_str and existing.expiry_date:
            try:
                claimed_expiry = date.fromisoformat(claimed_expiry_str)
                if claimed_expiry != existing.expiry_date:
                    conflicts.append(ConflictRecord(
                        field=f"certifications.{cert_type}.expiry_date",
                        claimed=str(claimed_expiry),
                        actual_on_record=str(existing.expiry_date),
                        note=(
                            f"Document states {cert_type} expiry as {claimed_expiry}, "
                            f"but our records show {existing.expiry_date}. "
                            f"Using stored date for scoring — flagged for review."
                        ),
                    ))
            except ValueError:
                logger.warning(
                    "Could not parse claimed_expiry %r as a date — skipping conflict check",
                    claimed_expiry_str,
                )

    # ── Check data access scope ──────────────────────────────────────────────
    data_access = extracted.get("data_access") or {}

    if existing_scope is not None:
        claimed_pii = data_access.get("pii")
        if claimed_pii is not None and claimed_pii != existing_scope.pii_access:
            conflicts.append(ConflictRecord(
                field="data_access_scope.pii_access",
                claimed=claimed_pii,
                actual_on_record=existing_scope.pii_access,
                note=(
                    f"Document {'claims' if claimed_pii else 'denies'} PII access, "
                    f"but stored scope shows pii_access={existing_scope.pii_access}. "
                    f"Existing record retained for scoring; flagged for review."
                ),
            ))

        claimed_financial = data_access.get("financial")
        if claimed_financial is not None and claimed_financial != existing_scope.financial_access:
            conflicts.append(ConflictRecord(
                field="data_access_scope.financial_access",
                claimed=claimed_financial,
                actual_on_record=existing_scope.financial_access,
                note=(
                    f"Document {'claims' if claimed_financial else 'denies'} financial access, "
                    f"but stored scope shows financial_access={existing_scope.financial_access}. "
                    f"Existing record retained for scoring; flagged for review."
                ),
            ))

    if conflicts:
        logger.info(
            "Conflict checker found %d conflict(s) — stored both sides, not auto-resolved.",
            len(conflicts),
        )

    return conflicts
