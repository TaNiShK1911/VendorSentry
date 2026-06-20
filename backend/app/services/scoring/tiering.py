"""
Tiering — converts composite score + vendor conditions into a risk tier.

Tier rules are evaluated in priority order (CRITICAL first).
A vendor can satisfy multiple conditions; it always reports its highest tier.

Anomaly taxonomy (from PRD.md §7, must match vendor_labels.csv values):
    BREACHED_VENDOR_HIGH_ACCESS    → CRITICAL
    VENDOR_UNDER_INVESTIGATION     → CRITICAL
    HIGH_RISK_SCORE                → HIGH  (composite > 80)
    EXPIRED_CERTIFICATION          → HIGH or MEDIUM
    RECENTLY_BREACHED_VENDOR       → MEDIUM
    CONTRACT_EXPIRED_ACTIVE_ACCESS → MEDIUM
    ELEVATED_RISK_VENDOR           → LOW   (composite 65–80)

Red/Yellow/Green rollup:
    CRITICAL, HIGH → RED
    MEDIUM, LOW    → YELLOW
    CLEAR          → GREEN
"""
from datetime import date, datetime
from typing import Sequence, Optional

from app.models.vendor import Vendor
from app.models.breach import BreachEvent
from app.models.certification import Certification
from app.models.data_access import DataAccessScope


# Score thresholds
_HIGH_RISK_THRESHOLD: float = 80.0
_ELEVATED_RISK_LOWER: float = 65.0
_ELEVATED_RISK_UPPER: float = 80.0

# Recency window for "recently breached"
_RECENT_BREACH_MONTHS: int = 12

_TIER_TO_COLOR: dict[str, str] = {
    "CRITICAL": "RED",
    "HIGH": "RED",
    "MEDIUM": "YELLOW",
    "LOW": "YELLOW",
    "CLEAR": "GREEN",
}


def _has_recent_breach(breaches: Sequence[BreachEvent]) -> bool:
    """Return True if any breach occurred within the last 12 months."""
    from datetime import timedelta
    cutoff = datetime.utcnow().date() - timedelta(days=_RECENT_BREACH_MONTHS * 30.44)
    return any(
        b.breach_date is not None and b.breach_date >= cutoff
        for b in breaches
    )


def _has_sensitive_access(scope: Optional[DataAccessScope]) -> bool:
    """Return True if vendor has PII or financial access."""
    if scope is None:
        return False
    return scope.pii_access or scope.financial_access


def _has_expired_cert(certs: Sequence[Certification]) -> bool:
    today = datetime.utcnow().date()
    return any(
        c.status == "expired" or (c.expiry_date and c.expiry_date < today)
        for c in certs
    )


def _contract_expired_with_access(
    contract_end: Optional[date],
    contract_status: Optional[str],
) -> bool:
    """
    Return True if contract end date has passed but vendor still has active status.
    A contract_status of 'active' despite an expired date signals orphaned access.
    """
    if contract_end is None:
        return False
    today = datetime.utcnow().date()
    expired = contract_end < today
    still_active = contract_status in ("active", None)
    return expired and still_active


def determine_tier(
    composite_score: float,
    vendor: Vendor,
    breaches: Sequence[BreachEvent],
    certs: Sequence[Certification],
    scope: Optional[DataAccessScope],
) -> tuple[str, list[str], str]:
    """
    Determine the risk tier, anomaly types, and status colour for a vendor.

    Rules are evaluated in priority order (CRITICAL first).
    All matching anomaly_types are collected; the highest tier is returned.

    Args:
        composite_score: The already-computed weighted composite (0–100).
        vendor: The Vendor ORM object (for investigation flag, contract dates).
        breaches: All BreachEvent rows for this vendor.
        certs: All Certification rows for this vendor.
        scope: DataAccessScope for this vendor (may be None).

    Returns:
        (tier, anomaly_types, status_color)
        tier        → "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "CLEAR"
        anomaly_types → list of anomaly type strings (may be empty)
        status_color → "RED" | "YELLOW" | "GREEN"
    """
    anomaly_types: list[str] = []
    tier_priority = ["CLEAR", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    current_tier = "CLEAR"

    def _upgrade(new_tier: str) -> None:
        nonlocal current_tier
        if tier_priority.index(new_tier) > tier_priority.index(current_tier):
            current_tier = new_tier

    # ── CRITICAL conditions ─────────────────────────────────────────────────
    if vendor.under_investigation:
        anomaly_types.append("VENDOR_UNDER_INVESTIGATION")
        _upgrade("CRITICAL")

    if _has_recent_breach(breaches) and _has_sensitive_access(scope):
        if "BREACHED_VENDOR_HIGH_ACCESS" not in anomaly_types:
            anomaly_types.append("BREACHED_VENDOR_HIGH_ACCESS")
        _upgrade("CRITICAL")

    # ── HIGH conditions ─────────────────────────────────────────────────────
    if composite_score > _HIGH_RISK_THRESHOLD:
        anomaly_types.append("HIGH_RISK_SCORE")
        _upgrade("HIGH")

    if _has_expired_cert(certs):
        anomaly_types.append("EXPIRED_CERTIFICATION")
        # HIGH if sensitive access, otherwise MEDIUM
        if _has_sensitive_access(scope):
            _upgrade("HIGH")
        else:
            _upgrade("MEDIUM")

    # ── MEDIUM conditions ───────────────────────────────────────────────────
    if _has_recent_breach(breaches) and not _has_sensitive_access(scope):
        # Recent breach but not high-access → MEDIUM (already CRITICAL if high-access)
        if "RECENTLY_BREACHED_VENDOR" not in anomaly_types:
            anomaly_types.append("RECENTLY_BREACHED_VENDOR")
        _upgrade("MEDIUM")

    if _contract_expired_with_access(vendor.contract_end, vendor.contract_status):
        anomaly_types.append("CONTRACT_EXPIRED_ACTIVE_ACCESS")
        _upgrade("MEDIUM")

    # ── LOW conditions ──────────────────────────────────────────────────────
    if _ELEVATED_RISK_LOWER <= composite_score <= _ELEVATED_RISK_UPPER:
        if "ELEVATED_RISK_VENDOR" not in anomaly_types:
            anomaly_types.append("ELEVATED_RISK_VENDOR")
        _upgrade("LOW")

    status_color = _TIER_TO_COLOR[current_tier]
    return current_tier, anomaly_types, status_color
