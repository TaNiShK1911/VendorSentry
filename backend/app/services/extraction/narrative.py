"""
Narrative generation — post-scoring, grounded risk rationale.

IMPLEMENTATION_PLAN.md §3 "Narrative Generation (after, never before, scoring)":
    "Separate, smaller LLM call: given the already-computed subscores +
    structured facts, produce a 2–4 sentence rationale."

ARCHITECTURAL RULES:
1. This function is called ONLY after score_vendor() has returned.
2. It receives structured facts (subscores, anomaly_types), NOT raw docs.
3. It cannot see or reference unverified/unstructured document text.
4. It MUST NOT output a risk score, tier, or status color.
5. The output is attached to VendorScore.rationale (informational only).
"""
from __future__ import annotations

import json
import logging

from app.services.extraction.llm_client import get_llm_client

logger = logging.getLogger(__name__)

_NARRATIVE_SYSTEM = """You are a risk communication specialist for VendorSentry.

Your job is to write a 2–4 sentence plain-English risk narrative for a vendor, \
based ONLY on the structured facts provided. You MUST follow these rules:

1. Only reference facts explicitly present in the input data — no invented claims.
2. Do NOT include a risk score, tier name, or Red/Yellow/Green status in your output.
3. Do NOT use vague language like "this vendor may have issues." Be specific.
4. Focus on the most impactful factors (highest subscores, flagged anomalies).
5. Respond with ONLY the narrative text (1–4 sentences). No JSON, no headings."""


def generate_rationale(
    vendor_name: str,
    composite_score: float,
    tier: str,
    breach_subscore: float,
    access_subscore: float,
    compliance_subscore: float,
    financial_subscore: float,
    anomaly_types: list[str],
) -> str:
    """
    Generate a grounded 2–4 sentence risk narrative.

    This function is called AFTER scoring — it reads subscores and anomaly types
    but never sees raw document text or unverified LLM extraction output.

    Args:
        vendor_name:        Human-readable vendor name.
        composite_score:    Already-computed composite (0–100).
        tier:               Already-determined tier string.
        *_subscore:         All four sub-scores (already computed).
        anomaly_types:      List of detected anomaly type strings.

    Returns:
        Plain-English narrative string (2–4 sentences).
    """
    # Build a tightly scoped fact block — no raw text, no unverified claims
    facts = {
        "vendor_name": vendor_name,
        "composite_score": composite_score,
        "subscores": {
            "breach_impact": round(breach_subscore, 1),
            "data_access_risk": round(access_subscore, 1),
            "compliance_health": round(compliance_subscore, 1),
            "financial_stability_risk": round(financial_subscore, 1),
        },
        "detected_anomalies": anomaly_types,
        "subscore_scale": "0 = no risk contribution, 100 = maximum risk contribution",
    }

    user_prompt = (
        f"Write a concise risk narrative for the following vendor based on these "
        f"already-computed risk facts. Explain what is driving the risk and what "
        f"should concern a security team most.\n\n"
        f"VENDOR FACTS:\n{json.dumps(facts, indent=2)}"
    )

    try:
        client = get_llm_client()
        narrative = client.complete(_NARRATIVE_SYSTEM, user_prompt).strip()
        # Sanity check: strip any score/tier that slipped through
        narrative = _strip_forbidden_content(narrative)
        return narrative
    except Exception as exc:
        logger.warning(
            "Narrative generation failed for vendor %r: %s. Using fallback.", vendor_name, exc
        )
        return _fallback_narrative(vendor_name, anomaly_types, composite_score)


def _strip_forbidden_content(text: str) -> str:
    """
    Remove any accidental score/tier references from the narrative.
    A belt-and-suspenders guard in case the LLM ignored the system prompt.
    """
    forbidden_phrases = [
        "risk score", "composite score", "tier:", "risk tier",
        "RED", "YELLOW", "GREEN", "CRITICAL tier", "HIGH tier",
    ]
    for phrase in forbidden_phrases:
        if phrase.lower() in text.lower():
            logger.warning(
                "Narrative contained forbidden phrase %r — stripping. Full text: %s",
                phrase, text[:200],
            )
            # Return a safe fallback rather than a corrupted narrative
            return _fallback_narrative("this vendor", [], 0)
    return text


def _fallback_narrative(
    vendor_name: str,
    anomaly_types: list[str],
    composite_score: float,
) -> str:
    """Deterministic fallback when the LLM call fails."""
    if not anomaly_types:
        return (
            f"{vendor_name} has no flagged anomalies at this time. "
            f"Continue standard monitoring cadence."
        )
    flags = ", ".join(a.replace("_", " ").title() for a in anomaly_types[:3])
    return (
        f"{vendor_name} has been flagged for: {flags}. "
        f"Review the subscore breakdown for the specific contributing factors "
        f"and consult the evidence trail for supporting documentation."
    )
