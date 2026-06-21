"""
Breach-to-vendor matching logic.

Two match strategies:
    1. Domain match (confidence=1.0): vendor.website_domain == breach["Domain"]
       — case-insensitive, only if both are non-empty. This is the only match
       type that auto-creates a BreachEvent.

    2. Fuzzy name match (confidence < 1.0): uses difflib.SequenceMatcher to
       compare vendor.name against breach["Title"] and breach["Name"].
       Only attempted when no domain match exists for that vendor.
       Threshold: 0.85 — below this we don't even return a match.
       Fuzzy matches produce a flagged EvidenceSignal for human review,
       never a BreachEvent.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.vendor import Vendor


@dataclass
class BreachMatch:
    """A single vendor-to-breach match result."""

    breach: dict  # the raw HIBP catalog entry
    confidence: float  # 1.0 = certain domain match, <1.0 = fuzzy name match
    match_type: str  # "domain" | "fuzzy_name"


# Minimum similarity ratio for fuzzy name matching.
# 0.85 is deliberately conservative — we'd rather miss an uncertain match
# than flood the review queue with noise.
_FUZZY_THRESHOLD = 0.85


def _domain_matches(vendor_domain: str | None, breach_domain: str | None) -> bool:
    """Case-insensitive domain comparison, only if both are non-empty."""
    if not vendor_domain or not breach_domain:
        return False
    return vendor_domain.strip().lower() == breach_domain.strip().lower()


def _fuzzy_score(vendor_name: str, breach_text: str) -> float:
    """Return SequenceMatcher ratio between vendor name and a breach text field."""
    return difflib.SequenceMatcher(
        None,
        vendor_name.lower(),
        breach_text.lower(),
    ).ratio()


def match_vendor_to_breaches(
    vendor: "Vendor",
    catalog: list[dict],
) -> list[BreachMatch]:
    """
    Match a vendor against the full HIBP breach catalog.

    Returns a list of BreachMatch objects. Domain matches come first.
    For a given vendor, fuzzy matching is only attempted when there are
    no domain matches at all.

    Args:
        vendor: The Vendor ORM object (needs .website_domain and .name).
        catalog: The list of HIBP breach dicts.

    Returns:
        List of BreachMatch objects, sorted by confidence descending.
    """
    domain_matches: list[BreachMatch] = []
    fuzzy_matches: list[BreachMatch] = []

    for breach in catalog:
        breach_domain = breach.get("Domain", "")

        # Strategy 1: exact domain match
        if _domain_matches(vendor.website_domain, breach_domain):
            domain_matches.append(
                BreachMatch(
                    breach=breach,
                    confidence=1.0,
                    match_type="domain",
                )
            )
            continue  # don't also fuzzy-match the same breach

        # Strategy 2: fuzzy name match (only if no domain set or domain didn't match)
        breach_title = breach.get("Title", "")
        breach_name = breach.get("Name", "")

        best_score = 0.0
        for text in (breach_title, breach_name):
            if text:
                score = _fuzzy_score(vendor.name, text)
                best_score = max(best_score, score)

        if best_score >= _FUZZY_THRESHOLD:
            fuzzy_matches.append(
                BreachMatch(
                    breach=breach,
                    confidence=round(best_score, 3),
                    match_type="fuzzy_name",
                )
            )

    # If we found domain matches, return only those — don't add fuzzy noise
    if domain_matches:
        return domain_matches

    # Otherwise return fuzzy matches sorted by confidence descending
    fuzzy_matches.sort(key=lambda m: m.confidence, reverse=True)
    return fuzzy_matches
