"""
Severity inference from HIBP breach data.

Maps real breach metadata (DataClasses, PwnCount, flags) to the severity
strings expected by subscore_breach.py's _SEVERITY_WEIGHTS dict:
    CRITICAL | HIGH | MEDIUM | LOW

This replaces the old random.choice(["HIGH", "MEDIUM"]) mock.

Thresholds and reasoning (documented per the pattern in subscore_compliance.py):

    CRITICAL — Sensitive data (passwords, financial, government IDs, security
    Q&A) at massive scale (>10M records). These represent nation-state-scale
    credential dumps that could affect many downstream services.

    HIGH — Sensitive data classes present but below the mega-breach threshold,
    OR the breach is flagged as sensitive/verified by HIBP. The presence of
    passwords or financial data at any scale is a serious signal.

    MEDIUM — Only email addresses and low-sensitivity metadata (names, IPs,
    usernames). Common in marketing-list leaks and low-impact scrapes.

    LOW — Anything else: very old, very small, spam-list-adjacent, or
    unverified breaches with no sensitive data classes.
"""
from __future__ import annotations

# DataClasses values that indicate high-sensitivity data
_CRITICAL_DATA_CLASSES = {
    "Passwords",
    "Financial data",
    "Government issued IDs",
    "Security questions and answers",
}

# DataClasses that are moderately sensitive
_HIGH_DATA_CLASSES = {
    "Credit cards",
    "Bank account numbers",
    "Social security numbers",
    "Partial credit card data",
    "Auth tokens",
    "Private messages",
}

# Threshold for CRITICAL: must be both sensitive AND massive scale
_CRITICAL_PWNCOUNT_THRESHOLD = 10_000_000

# Threshold for HIGH: a breach needs some scale to matter
_HIGH_PWNCOUNT_THRESHOLD = 100_000


def infer_severity(breach: dict) -> str:
    """
    Infer a severity string from HIBP breach metadata.

    Args:
        breach: A single HIBP breach catalog entry dict with keys like
                "DataClasses", "PwnCount", "IsSensitive", "IsVerified".

    Returns:
        One of "CRITICAL", "HIGH", "MEDIUM", "LOW" — matching the keys
        in subscore_breach.py's _SEVERITY_WEIGHTS dict exactly.
    """
    data_classes = set(breach.get("DataClasses", []))
    pwn_count = breach.get("PwnCount", 0) or 0
    is_sensitive = breach.get("IsSensitive", False)
    is_verified = breach.get("IsVerified", False)

    has_critical_data = bool(data_classes & _CRITICAL_DATA_CLASSES)
    has_high_data = bool(data_classes & _HIGH_DATA_CLASSES)

    # CRITICAL: sensitive data at massive scale
    if has_critical_data and pwn_count > _CRITICAL_PWNCOUNT_THRESHOLD:
        return "CRITICAL"

    # HIGH: sensitive data at smaller scale, OR high-sensitivity classes,
    # OR HIBP's own sensitivity/verified flags indicate severity
    if has_critical_data or has_high_data:
        return "HIGH"
    if is_sensitive and is_verified:
        return "HIGH"
    if is_sensitive and pwn_count > _HIGH_PWNCOUNT_THRESHOLD:
        return "HIGH"

    # MEDIUM: only email/username-level data, or verified breaches
    # of moderate scale
    email_level_classes = {"Email addresses", "Usernames", "IP addresses", "Names"}
    if data_classes and data_classes.issubset(email_level_classes):
        return "MEDIUM"
    if is_verified and pwn_count > _HIGH_PWNCOUNT_THRESHOLD:
        return "MEDIUM"

    # LOW: everything else — old, small, spam-list, unverified
    if not data_classes:
        return "LOW"

    return "MEDIUM"  # default for anything that doesn't fit the above
