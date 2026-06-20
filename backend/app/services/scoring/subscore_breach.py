"""
Breach subscore — recency-decayed impact of all breach events.

Formula (per IMPLEMENTATION_PLAN.md §4):
    for each breach:
        contribution = severity_weight * exp(-months_since_breach / 12)
    breach_subscore = min(100, sum(contributions) * 100)

Severity weights:
    CRITICAL = 1.0
    HIGH     = 0.7
    MEDIUM   = 0.4
    LOW      = 0.2

Special rule: if vendor has `under_investigation=True`,
breach_subscore is forced to 100 regardless of breach history.
"""
import math
from datetime import date, datetime
from typing import Sequence

from app.models.breach import BreachEvent


# Severity → weight mapping per the spec
_SEVERITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 1.0,
    "HIGH": 0.7,
    "MEDIUM": 0.4,
    "LOW": 0.2,
}

# Decay constant: 12 months half-life feels right — a breach from
# a year ago has exp(-1) ≈ 37% of its original weight.
_DECAY_MONTHS: float = 12.0


def _months_since(breach_date: date | None) -> float:
    """Return fractional months from breach_date to today. Unknown dates → 0 (max impact)."""
    if breach_date is None:
        return 0.0
    today = datetime.utcnow().date()
    delta_days = (today - breach_date).days
    # Clamp to 0 in case breach_date is in the future (data error)
    return max(0.0, delta_days / 30.44)


def compute_breach_subscore(
    breaches: Sequence[BreachEvent],
    under_investigation: bool = False,
) -> float:
    """
    Compute the breach subscore (0–100).

    Args:
        breaches: All BreachEvent rows for this vendor.
        under_investigation: If True, returns 100 immediately.

    Returns:
        float in [0, 100].
    """
    # Hard override — investigation always maxes out the subscore
    if under_investigation:
        return 100.0

    if not breaches:
        return 0.0

    total = 0.0
    for breach in breaches:
        weight = _SEVERITY_WEIGHTS.get(breach.severity, 0.2)
        months = _months_since(breach.breach_date)
        contribution = weight * math.exp(-months / _DECAY_MONTHS)
        total += contribution

    # Scale so a single CRITICAL breach today = 100
    return min(100.0, total * 100.0)
