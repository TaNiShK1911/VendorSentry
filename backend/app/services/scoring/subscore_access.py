"""
Access subscore — based on data sensitivity level.

Formula (per IMPLEMENTATION_PLAN.md §4):
    base = 20
    + 40  if pii_access
    + 30  if financial_access
    + 10  if broad_system_access

Max: 20 + 40 + 30 + 10 = 100
Min: 20 (every vendor gets a base risk simply for having access)
"""
from typing import Optional

from app.models.data_access import DataAccessScope


def compute_access_subscore(scope: Optional[DataAccessScope]) -> float:
    """
    Compute the access subscore (0–100).

    Args:
        scope: DataAccessScope ORM object, or None if no scope data exists.
               None is treated as minimal access (base = 20).

    Returns:
        float in [20, 100].
    """
    if scope is None:
        # No scope recorded → assume minimal access but still get base penalty
        return 20.0

    score = 20.0

    if scope.pii_access:
        score += 40.0

    if scope.financial_access:
        score += 30.0

    if scope.broad_system_access:
        score += 10.0

    return min(100.0, score)
