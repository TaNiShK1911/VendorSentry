"""
Financial subscore — maps financial health signal to a risk score.

Formula (per IMPLEMENTATION_PLAN.md §4):
    stable    → 10   (low risk)
    watch     → 50   (moderate risk)
    distressed → 90  (high risk)
    unknown   → 40   (penalized — absence of signal is itself a risk)

The `unknown` penalty (40) is intentional: if we have no financial data
on a vendor with sensitive access, that uncertainty must count against
them rather than being optimistically zeroed out.
"""
from typing import Literal

# Explicit type for the valid signal values
FinancialHealthSignal = Literal["stable", "watch", "distressed", "unknown"]

_SIGNAL_TO_SCORE: dict[str, float] = {
    "stable": 10.0,
    "watch": 50.0,
    "distressed": 90.0,
    "unknown": 40.0,
}


def compute_financial_subscore(financial_health_signal: str) -> float:
    """
    Compute the financial subscore (0–100).

    Args:
        financial_health_signal: One of "stable", "watch", "distressed", "unknown".
                                  Any unrecognized value is treated as "unknown".

    Returns:
        float in {10, 40, 50, 90}.
    """
    return _SIGNAL_TO_SCORE.get(financial_health_signal, _SIGNAL_TO_SCORE["unknown"])
