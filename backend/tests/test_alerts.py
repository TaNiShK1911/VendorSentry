from typing import Optional
from datetime import datetime
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.models import Vendor, BreachEvent, Certification, DataAccessScope, Alert, AlertType, AlertSeverity
from app.services.scoring.tiering import determine_tier
from app.services.alerts.generator import create_alert
from app.core.database import get_db

@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]


def test_generate_alerts_severity_matches_tiering(db_session: Session, setup_test_vendor: Vendor):
    """
    Test that determine_tier correctly assigns severity to each anomaly type 
    (including the EXPIRED_CERTIFICATION edge case with/without access).
    """
    vendor = setup_test_vendor
    vendor.under_investigation = True # CRITICAL
    
    breach = BreachEvent(id="b1", vendor_id=vendor.id, severity="HIGH", breach_date=datetime.utcnow().date())
    db_session.add(breach)
    
    cert = Certification(id="c1", vendor_id=vendor.id, status="expired", cert_type="SOC2_TYPE2")
    db_session.add(cert)
    
    scope_high = DataAccessScope(id="s1", vendor_id=vendor.id, pii_access=True)
    db_session.add(scope_high)
    db_session.flush()

    # With high access
    tier, anomalies, color = determine_tier(
        composite_score=85.0, # HIGH_RISK_SCORE
        vendor=vendor,
        breaches=[breach],
        certs=[cert],
        scope=scope_high
    )
    
    anomalies_dict = dict(anomalies)
    
    assert anomalies_dict.get("VENDOR_UNDER_INVESTIGATION") == "CRITICAL"
    assert anomalies_dict.get("BREACHED_VENDOR_HIGH_ACCESS") == "CRITICAL"
    assert anomalies_dict.get("HIGH_RISK_SCORE") == "HIGH"
    assert anomalies_dict.get("EXPIRED_CERTIFICATION") == "HIGH" # because of scope_high
    
    # Without high access
    scope_high.pii_access = False
    scope_high.financial_access = False
    db_session.flush()

    tier2, anomalies2, color2 = determine_tier(
        composite_score=75.0, # ELEVATED_RISK_VENDOR
        vendor=vendor,
        breaches=[breach],
        certs=[cert],
        scope=scope_high
    )
    
    anomalies_dict2 = dict(anomalies2)
    assert anomalies_dict2.get("RECENTLY_BREACHED_VENDOR") == "MEDIUM"
    assert anomalies_dict2.get("ELEVATED_RISK_VENDOR") == "LOW"
    assert anomalies_dict2.get("EXPIRED_CERTIFICATION") == "MEDIUM" # because of scope_low


def test_alerts_summary_by_type_counts_all_types(db_session: Session, client: TestClient, setup_test_vendor: Vendor):
    """
    Test that the summary endpoint dynamically groups by ALL Alert.type values.
    """
    create_alert(
        db=db_session,
        vendor_id=setup_test_vendor.id,
        vendor_name=setup_test_vendor.name,
        alert_type=AlertType.CERT_EXPIRING,
        severity=AlertSeverity.HIGH,
        message="Test cert expiring"
    )
    
    create_alert(
        db=db_session,
        vendor_id=setup_test_vendor.id,
        vendor_name=setup_test_vendor.name,
        alert_type=AlertType.EXPIRED_CERTIFICATION,
        severity=AlertSeverity.HIGH,
        message="Test expired certification"
    )
    
    response = client.get("/api/v1/alerts/summary")
    assert response.status_code == 200
    data = response.json()
    
    by_type = data["by_type"]
    assert "CERT_EXPIRING" in by_type
    assert by_type["CERT_EXPIRING"] == 1
    assert "EXPIRED_CERTIFICATION" in by_type
    assert by_type["EXPIRED_CERTIFICATION"] == 1


def test_alerts_summary_by_severity_includes_medium_and_low(db_session: Session, client: TestClient, setup_test_vendor: Vendor):
    """
    Test that medium and low severity counts are correctly aggregated.
    """
    create_alert(
        db=db_session,
        vendor_id=setup_test_vendor.id,
        vendor_name=setup_test_vendor.name,
        alert_type=AlertType.ELEVATED_RISK_VENDOR,
        severity=AlertSeverity.LOW,
        message="Test low severity"
    )
    
    create_alert(
        db=db_session,
        vendor_id=setup_test_vendor.id,
        vendor_name=setup_test_vendor.name,
        alert_type=AlertType.RECENTLY_BREACHED_VENDOR,
        severity=AlertSeverity.MEDIUM,
        message="Test medium severity"
    )
    
    response = client.get("/api/v1/alerts/summary")
    assert response.status_code == 200
    data = response.json()
    
    by_severity = data["by_severity"]
    assert by_severity["low"] == 1
    assert by_severity["medium"] == 1
    assert by_severity["high"] == 0
    assert by_severity["critical"] == 0
    assert data["total_open"] == 2
