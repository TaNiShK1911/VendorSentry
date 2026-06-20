"""
Pydantic schemas for extraction jobs and evidence signals.
Matches BACKEND_INTEGRATION.md §4 exactly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field


class ConflictRecord(BaseModel):
    """
    Represents a disagreement between LLM-extracted data and stored structured fields.
    
    ARCHITECTURAL RULE: conflicts are NEVER auto-resolved by the backend.
    Both sides are stored and surfaced to the user.
    """
    field: str
    claimed: Any            # What the LLM/document claims
    actual_on_record: Any   # What the DB currently holds
    note: str               # Human-readable explanation


class DataAccessExtracted(BaseModel):
    pii: bool = False
    financial: bool = False
    systems: List[str] = Field(default_factory=list)


class ComplianceClaim(BaseModel):
    type: str                           # e.g. "SOC2_TYPE2"
    claimed_status: str                 # "current" | "expired"
    claimed_expiry: Optional[str] = None  # ISO date string


class SLATerms(BaseModel):
    uptime_pct: Optional[float] = None
    breach_notification_hours: Optional[int] = None
    other: Dict[str, Any] = Field(default_factory=dict)


class StructuredExtractionOutput(BaseModel):
    """
    The only shape the LLM is permitted to return.
    Does NOT include composite_score or tier — those are computed separately.
    """
    data_access: Optional[DataAccessExtracted] = None
    compliance_claims: List[ComplianceClaim] = Field(default_factory=list)
    sla_terms: Optional[SLATerms] = None
    conflicts: List[ConflictRecord] = Field(default_factory=list)


class ExtractionJobCreate(BaseModel):
    vendor_id: str
    document_type: str  # contract | security_assessment | audit_report
    text: Optional[str] = None


class ExtractionJobOut(BaseModel):
    """Returned by GET /extraction-jobs/{job_id}."""
    id: str
    vendor_id: str
    document_type: str
    status: str          # pending | processing | done | failed
    structured_output: Optional[StructuredExtractionOutput] = None
    conflicts: List[ConflictRecord] = Field(default_factory=list)
    confidence: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EvidenceSignalOut(BaseModel):
    """Returned in GET /vendors/{id}/evidence list."""
    id: str
    source: str          # breach_db | public_records | status_api
    signal_type: str     # new_breach | financial_health_change | cert_status_change | regulatory_action
    received_at: datetime
    payload: Dict[str, Any]
    consumed_by_score_id: Optional[str] = None

    model_config = {"from_attributes": True}
