"""Stub extraction service for Dev B testing (Dev A will implement real LLM extraction)"""
from typing import Dict, Any
from uuid import UUID


def extract_from_text(vendor_id: UUID, document_type: str, text: str) -> Dict[str, Any]:
    """
    STUB — mock extraction result.

    Dev A will replace with real LLM extraction that:
    - Calls Anthropic/OpenAI API
    - Parses contract obligations, security assessments, audit reports
    - Returns structured JSON with grounding/conflict detection
    """
    return {
        "data_access": {
            "pii": True,
            "financial": False,
            "systems": ["customer_db"]
        },
        "compliance_claims": [
            {
                "type": "SOC2_TYPE2",
                "claimed_status": "current",
                "claimed_expiry": "2026-12-31"
            }
        ],
        "sla_terms": {
            "uptime_pct": 99.9,
            "breach_notification_hours": 72
        },
        "conflicts": []
    }


def generate_narrative(vendor_id: UUID, subscores: Dict[str, float], facts: Dict[str, Any]) -> str:
    """
    STUB — mock narrative generation.

    Dev A will replace with real LLM narrative generation that:
    - Takes already-computed subscores + structured facts
    - Generates 2-4 sentence grounded rationale
    - Never invents facts not in the input
    """
    return "STUB: Mock narrative. Real implementation will generate grounded narrative from subscores and facts."
