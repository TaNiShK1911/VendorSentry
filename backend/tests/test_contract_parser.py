import pytest
from unittest.mock import patch, MagicMock
from app.services.extraction.contract_parser import extract_contract
from app.models import Vendor, VendorScore, Certification, ExtractionJob

def test_extract_contract_merges_and_scores(db_session, setup_test_vendor):
    vendor = db_session.query(Vendor).first()
    
    # Pre-add a certification so it doesn't flag a conflict
    cert = Certification(
        vendor_id=vendor.id,
        cert_type="SOC2 Type II",
        status="Valid",
    )
    db_session.add(cert)
    db_session.commit()
    
    # The current LLM logic mocks checking and merges output
    # We will mock the LLM client to return a conflict-free JSON
    mock_output = {
        "data_access": {"pii": "Yes", "financial": "No", "systems": ["CRM"]},
        "compliance_claims": [{"type": "SOC2 Type II", "claimed_status": "Valid", "claimed_expiry": "2030-12-31"}],
        "sla_terms": {"uptime_pct": 99.9, "breach_notification_hours": 24, "other": {}},
        "conflicts": []
    }
    
    with patch("app.services.extraction.llm_client.LLMClient.complete_json", return_value=mock_output):
        job = ExtractionJob(vendor_id=vendor.id, source_type="contract_pdf", status="pending")
        db_session.add(job)
        db_session.commit()
        job = extract_contract(vendor, job, "fake text", db_session)
        
        assert job.status == "done"
        assert len(job.flagged_conflicts) == 0
        
        # Verify merge
        db_session.refresh(vendor)
        assert vendor.data_access_scope is not None
        assert vendor.data_access_scope.pii_access is True
        
        assert len(vendor.certifications) > 0
        assert any(c.cert_type == "SOC2 Type II" for c in vendor.certifications)
        
        # Verify rescore
        latest_score = db_session.query(VendorScore).filter_by(vendor_id=vendor.id).order_by(VendorScore.computed_at.desc()).first()
        assert latest_score.triggered_by == "extraction_complete"
