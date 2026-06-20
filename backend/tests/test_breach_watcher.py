import pytest
from unittest.mock import patch, MagicMock
from app.services.monitoring.breach_watcher import poll_breach_db
from app.models import Vendor, VendorScore, EvidenceSignal, BreachEvent

def test_poll_breach_db_success(db_session, setup_test_vendor):
    # Setup test vendor with initial score
    vendor = db_session.query(Vendor).filter_by(name="Test Vendor").first()
    
    # Mock random.random to return 0.0, ensuring the 1% chance branch always hits
    with patch("random.random", return_value=0.0):
        # We also need to mock create_new_breach_alert if we don't want to test it
        with patch("app.services.monitoring.breach_watcher.create_new_breach_alert") as mock_alert:
            with patch("app.services.monitoring.breach_watcher.SessionLocal", return_value=db_session):
                result = poll_breach_db()
            
                # Assert task completes without raising
                assert "new breaches detected" in result
            
                # Check EvidenceSignal is created and consumed_by_score_id is populated
                signal = db_session.query(EvidenceSignal).filter_by(vendor_id=vendor.id, signal_type="new_breach").first()
                assert signal is not None
                assert signal.consumed_by_score_id is not None
            
                # Check VendorScore is created
                score = db_session.query(VendorScore).filter_by(id=signal.consumed_by_score_id).first()
                assert score is not None
                assert score.triggered_by == "breach_detected"
                assert score.rationale is not None
            
                # Check BreachEvent is created
                breach = db_session.query(BreachEvent).filter_by(vendor_id=vendor.id).first()
                assert breach is not None
                assert breach.source == "breach_db"
                assert breach.description == f"Unauthorized access detected in {vendor.name} systems"
