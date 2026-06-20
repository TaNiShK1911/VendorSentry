"""Tests for alert endpoints"""
import pytest
from datetime import datetime

from app.models import Vendor, Alert, VendorType, ContractStatus, AlertType, AlertSeverity


def test_list_alerts(client, db):
    """Test listing alerts"""
    # Create vendor and alert
    vendor = Vendor(
        name="Test Vendor",
        type=VendorType.CLOUD_PROVIDER,
        contract_status=ContractStatus.ACTIVE,
        certifications=[],
        data_access_scope={},
        breach_history=[]
    )
    db.add(vendor)
    db.commit()

    alert = Alert(
        vendor_id=vendor.id,
        type=AlertType.CERT_EXPIRING,
        severity=AlertSeverity.HIGH,
        message="Test alert",
        dedup_key="test_key_123"
    )
    db.add(alert)
    db.commit()

    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_acknowledge_alert(client, db):
    """Test acknowledging an alert"""
    vendor = Vendor(
        name="Test Vendor",
        type=VendorType.CONTRACTOR,
        contract_status=ContractStatus.ACTIVE,
        certifications=[],
        data_access_scope={},
        breach_history=[]
    )
    db.add(vendor)
    db.commit()

    alert = Alert(
        vendor_id=vendor.id,
        type=AlertType.NEW_BREACH,
        severity=AlertSeverity.CRITICAL,
        message="Test breach alert",
        dedup_key="breach_test_key"
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    response = client.post(f"/api/v1/alerts/{alert.id}/acknowledge")
    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged_at"] is not None


def test_resolve_alert(client, db):
    """Test resolving an alert"""
    vendor = Vendor(
        name="Test Vendor",
        type=VendorType.PAYMENT_PROCESSOR,
        contract_status=ContractStatus.ACTIVE,
        certifications=[],
        data_access_scope={},
        breach_history=[]
    )
    db.add(vendor)
    db.commit()

    alert = Alert(
        vendor_id=vendor.id,
        type=AlertType.CONTRACT_EXPIRING,
        severity=AlertSeverity.MEDIUM,
        message="Contract expiring",
        dedup_key="contract_test_key"
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    resolution_data = {"resolution_note": "Contract renewed"}
    response = client.post(f"/api/v1/alerts/{alert.id}/resolve", json=resolution_data)
    assert response.status_code == 200
    data = response.json()
    assert data["resolved_at"] is not None


def test_alert_summary(client, db):
    """Test getting alert summary"""
    response = client.get("/api/v1/alerts/summary")
    assert response.status_code == 200
    data = response.json()
    assert "open_critical" in data
    assert "open_high" in data
    assert "open_total" in data
