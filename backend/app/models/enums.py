"""
Shared enumerations used across models.
"""
from enum import Enum


class RiskTier(str, Enum):
    """Risk tier enumeration matching TIERS in vendor_score.py"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    CLEAR = "CLEAR"


class StatusColor(str, Enum):
    """Status color enumeration matching STATUS_COLORS in vendor_score.py"""
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
