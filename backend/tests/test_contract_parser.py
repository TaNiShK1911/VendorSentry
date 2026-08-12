import pytest
import uuid
from unittest.mock import patch, MagicMock
from app.services.extraction.contract_parser import extract_contract
from app.models import Vendor, VendorScore, Certification, ExtractionJob


def test_extract_contract_merges_and_scores(db_session, setup_test_vendor):
    vendor = setup_test_vendor

    # Create the required ExtractionJob first
    job = ExtractionJob(
        id=str(uuid.uuid4()),
        vendor_id=vendor.id,
        source_type="contract_pdf",
        status="pending"
    )
    db_session.add(job)
    db_session.commit()

    mock_output = {
        "data_access": {"pii": "Yes", "financial": "No", "systems": ["CRM"]},
        "compliance_claims": [
            {"type": "SOC2", "claimed_status": "Valid", "claimed_expiry": "2030-12-31"}
        ],
        "sla_terms": {"uptime_pct": 99.9, "breach_notification_hours": 24, "other": {}},
        "conflicts": []
    }

    with patch("app.services.extraction.llm_client.LLMClient.complete_json",
               return_value=mock_output):
        result_job = extract_contract(
            vendor, job, "fake contract text", db_session,
            document_type="contract"
        )

    db_session.commit()
    db_session.refresh(vendor)

    assert result_job.status == "done"
    assert result_job.error_message is None

    # Merge check
    assert vendor.data_access_scope is not None
    assert vendor.data_access_scope.pii_access is True

    # Rescore check
    scores = db_session.query(VendorScore).filter_by(vendor_id=vendor.id).all()
    assert len(scores) >= 1
    latest = max(scores, key=lambda s: s.computed_at)
    assert latest.triggered_by == "extraction_complete"
    assert latest.rationale is not None and len(latest.rationale) > 10
