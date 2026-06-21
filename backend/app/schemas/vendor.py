"""
Pydantic schemas for Vendor — used by the API layer (Dev B).

Dev A defines these shapes here so both devs agree on the contract
before splitting. Matches BACKEND_INTEGRATION.md §2 exactly.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse


# --------------------------------------------------------------------------- #
# Nested schemas
# --------------------------------------------------------------------------- #

class ContactInfo(BaseModel):
    liaison_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class CertificationOut(BaseModel):
    id: str
    cert_type: str
    status: str
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    source: str

    model_config = {"from_attributes": True}


class BreachEventOut(BaseModel):
    id: str
    breach_date: Optional[date] = None
    severity: str
    source: str
    description: Optional[str] = None
    resolved: bool

    model_config = {"from_attributes": True}


class DataAccessScopeOut(BaseModel):
    pii_access: bool
    financial_access: bool
    broad_system_access: bool
    systems: List[str] = Field(default_factory=list)
    scope_notes: Optional[str] = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Request schemas (used by POST /vendors, PATCH /vendors/{id})
# --------------------------------------------------------------------------- #

def _normalize_domain(v: Optional[str]) -> Optional[str]:
    """Strip protocol, path, and lowercase a domain string."""
    if not v:
        return None
    v = v.strip().lower()
    # Handle URLs like "https://example.com/path"
    if "://" in v:
        parsed = urlparse(v)
        v = parsed.hostname or v
    # Strip any trailing path/slash
    v = v.split("/")[0]
    return v or None


class VendorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    vendor_type: str = "other"
    contact: Optional[ContactInfo] = None
    website_domain: Optional[str] = None
    annual_spend: Optional[float] = Field(None, ge=0)
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    contract_status: Optional[str] = None
    financial_health_signal: str = "unknown"
    financial_health_source: str = "unknown"
    under_investigation: bool = False

    # Scope fields
    has_pii_access: Optional[bool] = False
    has_financial_access: Optional[bool] = False
    systems_access: Optional[List[str]] = Field(default_factory=list)
    data_access_notes: Optional[str] = None

    @field_validator("website_domain", mode="before")
    @classmethod
    def normalize_website_domain(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_domain(v)


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    vendor_type: Optional[str] = None
    contact: Optional[ContactInfo] = None
    website_domain: Optional[str] = None
    annual_spend: Optional[float] = Field(None, ge=0)
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    contract_status: Optional[str] = None
    financial_health_signal: Optional[str] = None
    financial_health_source: Optional[str] = None
    under_investigation: Optional[bool] = None

    # Scope fields
    has_pii_access: Optional[bool] = None
    has_financial_access: Optional[bool] = None
    systems_access: Optional[List[str]] = None
    data_access_notes: Optional[str] = None

    @field_validator("website_domain", mode="before")
    @classmethod
    def normalize_website_domain(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_domain(v)


# --------------------------------------------------------------------------- #
# Response schemas
# --------------------------------------------------------------------------- #

class VendorListItem(BaseModel):
    """Returned by GET /vendors — backs the portfolio grid."""
    id: str
    name: str
    vendor_type: str
    tier: Optional[str] = None          # from current_score
    status_color: Optional[str] = None  # RED | YELLOW | GREEN
    composite_score: Optional[float] = None
    anomaly_types: List[str] = Field(default_factory=list)
    last_assessed_at: Optional[datetime] = None
    contract_end: Optional[date] = None
    has_pii_access: bool = False
    active_alert_count: int = 0

    model_config = {"from_attributes": True}


class VendorDetail(BaseModel):
    """Returned by GET /vendors/{id} — full drill-down profile."""
    id: str
    name: str
    vendor_type: str
    contact: Optional[ContactInfo] = None
    website_domain: Optional[str] = None
    annual_spend: Optional[float] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    contract_status: Optional[str] = None
    certifications: List[CertificationOut] = Field(default_factory=list)
    data_access_scope: Optional[DataAccessScopeOut] = None
    breach_history: List[BreachEventOut] = Field(default_factory=list)
    financial_health_signal: str
    financial_health_source: str
    under_investigation: bool
    last_assessed_at: Optional[datetime] = None
    current_score: Optional["VendorScoreOut"] = None
    score_history: List["VendorScoreOut"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImportResult(BaseModel):
    """Returned by POST /vendors/import."""
    rows_processed: int
    rows_succeeded: int
    rows_failed: int
    errors: List[dict] = Field(default_factory=list)


# Deferred import to avoid circular reference with scoring schema
from app.schemas.scoring import VendorScoreOut  # noqa: E402
VendorDetail.model_rebuild()
