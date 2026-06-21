"""
Follow-up suggestion generator.

Uses simple pattern matching on the query + answer text to propose
contextual next questions. No LLM is called — purely deterministic.
"""
from __future__ import annotations

import re


_BREACH_FOLLOWUPS = [
    "Which of these vendors have PII or financial access?",
    "Show the risk scores for breached vendors",
    "Are any of these vendors under active investigation?",
]

_CERT_FOLLOWUPS = [
    "Which vendors are highest risk overall?",
    "Do any of these vendors have open breach alerts?",
    "Show full details for the most critical certification issue",
]

_PORTFOLIO_FOLLOWUPS = [
    "Which vendors are in the CRITICAL tier?",
    "Show all open breach alerts",
    "Which vendors haven't been assessed in over a year?",
]

_VENDOR_FOLLOWUPS = [
    "Show all alerts for this vendor",
    "What is the breach history for this vendor?",
    "Which other vendors have a similar risk profile?",
]

_ASSESSMENT_FOLLOWUPS = [
    "What is the risk tier of overdue vendors?",
    "Do any of the overdue vendors have PII access?",
    "Show all critical alerts across the portfolio",
]

_DEFAULT_FOLLOWUPS = [
    "Show our highest-risk vendors",
    "What is the overall portfolio health?",
    "Are there any unresolved critical alerts?",
]


def generate_followups(query: str, answer: str) -> list[str]:
    """
    Return 2–3 contextual follow-up suggestions based on the query content.
    """
    q = (query + " " + answer).lower()

    if any(kw in q for kw in ("breach", "hibp", "compromised", "pwned")):
        return _BREACH_FOLLOWUPS[:3]

    if any(kw in q for kw in ("cert", "certification", "expir")):
        return _CERT_FOLLOWUPS[:3]

    if any(kw in q for kw in ("portfolio", "distribution", "overall", "health", "summary")):
        return _PORTFOLIO_FOLLOWUPS[:3]

    if any(kw in q for kw in ("assess", "overdue", "year", "haven't been")):
        return _ASSESSMENT_FOLLOWUPS[:3]

    if any(kw in q for kw in ("vendor", "detail", "profile", "score")):
        return _VENDOR_FOLLOWUPS[:3]

    return _DEFAULT_FOLLOWUPS[:3]
