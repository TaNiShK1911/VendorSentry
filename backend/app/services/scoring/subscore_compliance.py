"""
Compliance subscore -- based on certification health and assessment freshness.

Formula (per IMPLEMENTATION_PLAN.md section 4):
    compliance_subscore = 100
        - (40 if any required cert is expired)
        - (20 if any cert expires within 30 days and not yet renewed)
        - (15 if assessment overdue > 12 months since last_assessed_at)
    floor at 0

The score is a compliance-health contribution:
  100 = all certs current, assessment fresh
  0   = expired certs + expiring certs + overdue assessment

Tier rules (in tiering.py) apply direct condition checks ON TOP of
this subscore, e.g. "expired cert + sensitive access -> HIGH/MEDIUM".
The subscore feeds the weighted composite; the rules produce the
anomaly taxonomy required by the evaluation harness.
"""
from datetime import date, datetime, timedelta
from typing import Sequence, Optional

from app.models.certification import Certification

# Penalty constants
_PENALTY_EXPIRED: float = 40.0
_PENALTY_EXPIRING_SOON: float = 20.0   # expires within 30 days
_PENALTY_OVERDUE: float = 15.0         # no assessment in 12 months

_EXPIRING_SOON_DAYS: int = 30
_OVERDUE_MONTHS: int = 12


def _today() -> date:
    return datetime.utcnow().date()


def _has_expired_cert(certs: Sequence[Certification]) -> bool:
    """Return True if any cert is currently expired."""
    today = _today()
    for cert in certs:
        if cert.status == "expired":
            return True
        if cert.expiry_date and cert.expiry_date < today:
            return True
    return False


def _has_expiring_soon_cert(certs: Sequence[Certification]) -> bool:
    """Return True if any cert expires within EXPIRING_SOON_DAYS, or is pending renewal."""
    today = _today()
    threshold = today + timedelta(days=_EXPIRING_SOON_DAYS)
    for cert in certs:
        if cert.status == "pending_renewal":
            return True
        if cert.status in ("current", "unknown") and cert.expiry_date:
            if today <= cert.expiry_date <= threshold:
                return True
    return False


def _is_assessment_overdue(last_assessed_at: Optional[datetime]) -> bool:
    """Return True if last assessment was > 12 months ago (or never done)."""
    if last_assessed_at is None:
        return True  # Never assessed -> treat as overdue
    cutoff = datetime.utcnow() - timedelta(days=_OVERDUE_MONTHS * 30.44)
    return last_assessed_at < cutoff


def compute_compliance_subscore(
    certs: Sequence[Certification],
    last_assessed_at: Optional[datetime],
) -> float:
    """
    Compute the compliance subscore (0-100).

    Args:
        certs: All Certification rows for this vendor.
        last_assessed_at: Timestamp of the most recent security assessment.

    Returns:
        float in [0, 100]. 100 = fully compliant. 0 = all penalties hit.
    """
    score = 0.0

    if _has_expired_cert(certs):
        score += _PENALTY_EXPIRED

    if _has_expiring_soon_cert(certs):
        score += _PENALTY_EXPIRING_SOON

    if _is_assessment_overdue(last_assessed_at):
        score += _PENALTY_OVERDUE

    return min(100.0, score)


def get_compliance_flags(
    certs: Sequence[Certification],
    last_assessed_at: Optional[datetime],
) -> dict:
    """
    Return a dict of boolean flags for use by tiering.py.
    Keeps tiering logic readable without re-computing cert states.
    """
    return {
        "has_expired_cert": _has_expired_cert(certs),
        "has_expiring_soon_cert": _has_expiring_soon_cert(certs),
        "is_assessment_overdue": _is_assessment_overdue(last_assessed_at),
    }
