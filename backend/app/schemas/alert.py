"""
Pydantic schemas for the Alert resource.
Matches BACKEND_INTEGRATION.md §5.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


ALERT_TYPES = (
    "CERT_EXPIRING",
    "CONTRACT_EXPIRING",
    "ASSESSMENT_OVERDUE",
    "NEW_BREACH",
    "SCORE_TIER_CHANGED",
)

ALERT_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


class AlertOut(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    type: str
    severity: str
    message: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    dedup_key: Optional[str] = None

    model_config = {"from_attributes": True}


class AlertSummary(BaseModel):
    """Returned by GET /alerts/summary — backs the nav-bar badge."""
    open_critical: int
    open_high: int
    open_total: int


class AlertResolveRequest(BaseModel):
    resolution_note: Optional[str] = None
