"""
Extraction service package.
"""
from app.services.extraction.contract_parser import extract_contract
from app.services.extraction.compliance_summarizer import (
    summarise_audit_report,
    summarise_security_assessment,
)
from app.services.extraction.narrative import generate_rationale
from app.services.extraction.conflict_checker import check_conflicts
from app.services.extraction.llm_client import get_llm_client

__all__ = [
    "extract_contract",
    "summarise_audit_report",
    "summarise_security_assessment",
    "generate_rationale",
    "check_conflicts",
    "get_llm_client",
]
