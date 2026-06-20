"""Tests for scoring endpoints"""
import pytest

from app.models import Vendor, VendorScore, VendorType, ContractStatus, RiskTier, StatusColor


def test_portfolio_score_distribution(client, db):
    """Test getting portfolio score distribution"""
    response = client.get("/api/v1/portfolio/score-distribution")
    assert response.status_code == 200
    data = response.json()
    assert "by_tier" in data
    assert "by_status_color" in data
    assert "total_vendors" in data


def test_portfolio_score_trend(client, db):
    """Test getting portfolio score trend"""
    response = client.get("/api/v1/portfolio/score-trend?range=30d")
    assert response.status_code == 200
    data = response.json()
    assert "points" in data


def test_get_vendor_score(client, db):
    """Test getting vendor score"""
    # Create vendor
    vendor = Vendor(
        name="Test Vendor",
        type=VendorType.CLOUD_PROVIDER,
        contract_status=ContractStatus.ACTIVE,
        certifications=[],
        data_access_scope={"pii": True},
        breach_history=[]
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    # Create score
    score = VendorScore(
        vendor_id=vendor.id,
        breach_subscore=50.0,
        access_subscore=60.0,
        compliance_subscore=70.0,
        financial_subscore=40.0,
        composite_score=55.0,
        tier=RiskTier.MEDIUM,
        status_color=StatusColor.YELLOW,
        anomaly_types=[],
        rationale="Test rationale",
        triggered_by="manual"
    )
    db.add(score)
    db.commit()

    response = client.get(f"/api/v1/vendors/{vendor.id}/score")
    assert response.status_code == 200
    data = response.json()
    assert data["composite_score"] == 55.0
    assert data["tier"] == "MEDIUM"
    assert "subscores" in data


def test_rescore_vendor(client, db):
    """Test rescoring a vendor"""
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
    db.refresh(vendor)

    response = client.post(f"/api/v1/vendors/{vendor.id}/rescore")
    assert response.status_code == 200
    data = response.json()
    assert "composite_score" in data
    assert "tier" in data
