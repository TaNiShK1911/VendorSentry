"""
LLM prompt templates for document extraction.

One template per document_type:
  - contract          → data access permissions, SLAs, compliance requirements
  - security_assessment → Q&A-style questionnaire self-assessment
  - audit_report      → SOC 2 / ISO 27001 / PCI-DSS report summarisation

ARCHITECTURAL RULES:
1. Every prompt MUST demand strict JSON output matching StructuredExtractionOutput.
2. Prompts MUST NOT ask the LLM to produce a risk score, tier, or status color.
3. The grounding instruction tells the LLM to only assert facts present in the
   input — never to invent certifications, dates, or compliance claims.
4. The conflict instruction tells the LLM to flag disagreements rather than
   silently choosing one side.
"""
from string import Template

# ─────────────────────────────────────────────────────────────────────────────
# Shared system prompt injected before every extraction call
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a compliance data extraction assistant for VendorSentry, \
an AI-powered vendor risk intelligence platform.

Your ONLY job is to extract structured facts from vendor documents. \
You MUST follow these rules without exception:

1. OUTPUT FORMAT: Always respond with a single valid JSON object matching \
   the schema below. No markdown fences, no explanation text outside the JSON.

2. GROUNDING RULE: Only assert facts that are explicitly stated in the input document. \
   Do NOT invent, infer, or hallucinate certifications, expiry dates, or compliance claims.

3. CONFLICT RULE: If a document claim disagrees with the "existing_vendor_data" \
   provided in the user message, record both sides in the `conflicts` array. \
   Do NOT silently choose one side or discard either claim.

4. SCORE PROHIBITION: You MUST NOT output a risk score, risk tier, \
   or status color (RED/YELLOW/GREEN). These are computed separately by \
   deterministic code and are not your responsibility.

5. UNKNOWN VALUES: If a field is not present in the document, use null.

Required output schema:
{
  "data_access": {
    "pii": boolean or null,
    "financial": boolean or null,
    "systems": [list of system names as strings]
  },
  "compliance_claims": [
    {
      "type": "SOC2_TYPE1|SOC2_TYPE2|ISO_27001|PCI_DSS|GDPR_COMPLIANCE|HIPAA|OTHER",
      "claimed_status": "current|expired|pending_renewal|unknown",
      "claimed_expiry": "YYYY-MM-DD or null"
    }
  ],
  "sla_terms": {
    "uptime_pct": number or null,
    "breach_notification_hours": integer or null,
    "other": {}
  },
  "conflicts": [
    {
      "field": "field.path",
      "claimed": <value from document>,
      "actual_on_record": <value from existing_vendor_data>,
      "note": "plain English explanation"
    }
  ]
}"""

# ─────────────────────────────────────────────────────────────────────────────
# Per-document-type user prompt templates
# ─────────────────────────────────────────────────────────────────────────────

CONTRACT_PROMPT = Template("""Extract structured compliance and access facts from the following \
vendor contract document.

Focus on:
- Data access permissions: what customer data (PII, financial records) can this vendor access?
- Which internal systems are named as in-scope?
- SLA terms: uptime guarantees, breach notification timelines
- Compliance obligations: any SOC 2, ISO 27001, PCI-DSS, or GDPR requirements the vendor commits to

Existing vendor data on record (use this to detect conflicts):
$existing_vendor_data

CONTRACT DOCUMENT:
---
$document_text
---

Respond with ONLY the JSON object described in your system instructions.""")


SECURITY_ASSESSMENT_PROMPT = Template("""Extract structured compliance facts from the following \
vendor security assessment or questionnaire.

This document is a self-reported vendor response. Extract:
- Access scope: does the vendor acknowledge handling PII or financial data?
- Compliance certifications: what certs does the vendor claim (type, status, expiry)?
- Any SLA or breach notification commitments mentioned

Treat all claims as "self-reported" — they will be cross-checked against \
certified records separately.

Existing vendor data on record (use this to detect conflicts):
$existing_vendor_data

SECURITY ASSESSMENT DOCUMENT:
---
$document_text
---

Respond with ONLY the JSON object described in your system instructions.""")


AUDIT_REPORT_PROMPT = Template("""Extract structured compliance facts from the following \
audit report (SOC 2, ISO 27001, PCI-DSS, or similar).

Focus on:
- Certification type (SOC 2 Type I or II, ISO 27001, PCI-DSS Level)
- Certification status: is the opinion unqualified (current) or qualified/adverse?
- Audit period covered and expiry/renewal date if stated
- Any findings, exceptions, or material weaknesses noted
- Scope: what systems or services are covered?

Note: Audit reports are authoritative sources. If the report's findings \
contradict existing vendor data, record the conflict.

Existing vendor data on record (use this to detect conflicts):
$existing_vendor_data

AUDIT REPORT DOCUMENT:
---
$document_text
---

Respond with ONLY the JSON object described in your system instructions.""")


_TEMPLATES: dict[str, Template] = {
    "contract": CONTRACT_PROMPT,
    "security_assessment": SECURITY_ASSESSMENT_PROMPT,
    "audit_report": AUDIT_REPORT_PROMPT,
}


def build_user_prompt(
    document_type: str,
    document_text: str,
    existing_vendor_data: dict,
) -> str:
    """
    Render the user-turn prompt for the given document type.

    Args:
        document_type: "contract" | "security_assessment" | "audit_report"
        document_text: Raw text content of the document.
        existing_vendor_data: Dict of current structured vendor fields
                              (used by the LLM for conflict detection).

    Returns:
        Rendered prompt string.

    Raises:
        ValueError: if document_type is not recognised.
    """
    template = _TEMPLATES.get(document_type)
    if template is None:
        raise ValueError(
            f"Unknown document_type {document_type!r}. "
            f"Must be one of: {list(_TEMPLATES.keys())}"
        )
    return template.substitute(
        document_text=document_text,
        existing_vendor_data=str(existing_vendor_data),
    )
