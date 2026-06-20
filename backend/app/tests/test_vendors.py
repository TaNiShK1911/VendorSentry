"""Tests for vendor endpoints"""
import pytest

from app.models import Vendor, VendorType, ContractStatus


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_vendor(client, db):
    """Test creating a vendor"""
    vendor_data = {
        "name": "Test Vendor",
        "type": "cloud_provider",
        "annual_spend": 100000,
        "contract_status": "active",
        "certifications": [],
        "data_access_scope": {"pii": True, "financial": False, "systems": []},
        "breach_history": []
    }

    response = client.post("/api/v1/vendors", json=vendor_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Vendor"
    assert data["type"] == "cloud_provider"


def test_list_vendors(client, db):
    """Test listing vendors"""
    # Create a vendor first
    vendor = Vendor(
        name="Test Vendor 1",
        type=VendorType.CLOUD_PROVIDER,
        contract_status=ContractStatus.ACTIVE,
        certifications=[],
        data_access_scope={},
        breach_history=[]
    )
    db.add(vendor)
    db.commit()

    response = client.get("/api/v1/vendors")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total_items"] >= 1


def test_get_vendor(client, db):
    """Test getting a specific vendor"""
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

    response = client.get(f"/api/v1/vendors/{vendor.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Vendor"


def test_update_vendor(client, db):
    """Test updating a vendor"""
    vendor = Vendor(
        name="Old Name",
        type=VendorType.SOFTWARE_VENDOR,
        contract_status=ContractStatus.ACTIVE,
        certifications=[],
        data_access_scope={},
        breach_history=[]
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    update_data = {"name": "New Name"}
    response = client.patch(f"/api/v1/vendors/{vendor.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"


def test_delete_vendor(client, db):
    """Test soft-deleting a vendor"""
    vendor = Vendor(
        name="To Delete",
        type=VendorType.OTHER,
        contract_status=ContractStatus.ACTIVE,
        certifications=[],
        data_access_scope={},
        breach_history=[]
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    response = client.delete(f"/api/v1/vendors/{vendor.id}")
    assert response.status_code == 204

    # Verify soft delete
    db.refresh(vendor)
    assert vendor.archived_at is not None
