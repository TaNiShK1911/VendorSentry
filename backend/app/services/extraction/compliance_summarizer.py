"""
Compliance summariser — wraps contract_parser for audit-report-specific flow.

Implements IMPLEMENTATION_PLAN.md §3.4:
"LLM summarization job parses report structure (scope, opinion,
exceptions/findings, period covered) into structured compliance fields."

This is a thin wrapper: the audit_report prompt template already handles
the SOC 2 / ISO 27001 specifics. This module provides a named public
function to keep the import surface clear for Dev B.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.vendor import Vendor
from app.models.extraction_job import ExtractionJob
from app.services.extraction.contract_parser import extract_contract


def summarise_audit_report(
    vendor: Vendor,
    report_text: str,
    db: Session,
) -> ExtractionJob:
    """
    Summarise a SOC 2 / ISO 27001 / PCI-DSS audit report into structured fields.

    Args:
        vendor:      The Vendor ORM object.
        report_text: Raw text of the audit report.
        db:          SQLAlchemy session.

    Returns:
        ExtractionJob with document_type="audit_report".
    """
    return extract_contract(
        vendor=vendor,
        document_text=report_text,
        db=db,
        document_type="audit_report",
    )


def summarise_security_assessment(
    vendor: Vendor,
    assessment_text: str,
    db: Session,
) -> ExtractionJob:
    """
    Summarise a security questionnaire / self-assessment into structured fields.

    Args:
        vendor:          The Vendor ORM object.
        assessment_text: Raw text of the questionnaire.
        db:              SQLAlchemy session.

    Returns:
        ExtractionJob with document_type="security_assessment".
    """
    return extract_contract(
        vendor=vendor,
        document_text=assessment_text,
        db=db,
        document_type="security_assessment",
    )
