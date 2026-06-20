"""Vendor CRUD API endpoints"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, VendorScore, Alert, RiskTier, StatusColor
from app.schemas import (
    VendorCreate,
    VendorUpdate,
    VendorListItem,
    VendorDetail,
    PaginatedResponse,
    ImportResult,
    VendorScoreResponse,
    VendorContact,
)
from app.services.scoring.engine import score_vendor

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def list_vendors(
    q: Optional[str] = None,
    tier: Optional[str] = None,
    type: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    has_pii_access: Optional[bool] = None,
    cert_expiring_within_days: Optional[int] = None,
    sort: str = "score_desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List/search/filter vendors - backs the main portfolio grid"""
    query = db.query(Vendor).filter(Vendor.archived_at.is_(None))

    # Apply filters
    if q:
        query = query.filter(Vendor.name.ilike(f"%{q}%"))

    if type:
        query = query.filter(Vendor.type == type)

    # Get total count
    total_items = query.count()

    # Pagination
    offset = (page - 1) * page_size
    vendors = query.offset(offset).limit(page_size).all()

    # Build response items
    items = []
    for vendor in vendors:
        # Get latest score
        latest_score = db.query(VendorScore).filter(
            VendorScore.vendor_id == vendor.id
        ).order_by(VendorScore.computed_at.desc()).first()

        # Count active alerts
        alert_count = db.query(Alert).filter(
            Alert.vendor_id == vendor.id,
            Alert.resolved_at.is_(None)
        ).count()

        # Check PII access
        has_pii = vendor.data_access_scope.get("pii", False) if vendor.data_access_scope else False

        items.append(VendorListItem(
            id=vendor.id,
            name=vendor.name,
            type=vendor.type,
            tier=latest_score.tier if latest_score else RiskTier.CLEAR,
            status_color=latest_score.status_color if latest_score else StatusColor.GREEN,
            composite_score=latest_score.composite_score if latest_score else 0.0,
            anomaly_types=latest_score.anomaly_types if latest_score else [],
            last_assessed_at=vendor.last_assessed_at,
            contract_end=vendor.contract_end,
            has_pii_access=has_pii,
            active_alert_count=alert_count
        ))

    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages
    )


@router.get("/{vendor_id}", response_model=VendorDetail)
def get_vendor(vendor_id: UUID, db: Session = Depends(get_db)):
    """Get full vendor profile - drill-down view"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "VENDOR_NOT_FOUND", "message": f"Vendor {vendor_id} not found", "details": {}}}
        )

    # Get latest score
    latest_score = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor.id
    ).order_by(VendorScore.computed_at.desc()).first()

    # Get score history (last 10)
    score_history = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor.id
    ).order_by(VendorScore.computed_at.desc()).limit(10).all()

    return VendorDetail(
        id=vendor.id,
        name=vendor.name,
        type=vendor.type,
        contact=VendorContact(
            liaison_name=vendor.contact_name,
            email=vendor.contact_email
        ),
        annual_spend=vendor.annual_spend,
        contract_start=vendor.contract_start,
        contract_end=vendor.contract_end,
        contract_status=vendor.contract_status,
        certifications=vendor.certifications,
        data_access_scope=vendor.data_access_scope,
        breach_history=vendor.breach_history,
        financial_health_signal=vendor.financial_health_signal,
        financial_health_source=vendor.financial_health_source,
        last_assessed_at=vendor.last_assessed_at,
        current_score=latest_score,
        score_history=score_history,
        created_at=vendor.created_at,
        updated_at=vendor.updated_at
    )


@router.post("", response_model=VendorDetail, status_code=status.HTTP_201_CREATED)
def create_vendor(vendor_data: VendorCreate, db: Session = Depends(get_db)):
    """Create a vendor manually"""
    vendor = Vendor(**vendor_data.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    # Trigger initial scoring
    score = score_vendor(vendor, triggered_by="manual")
    db.add(score)
    db.commit()

    return get_vendor(vendor.id, db)


@router.patch("/{vendor_id}", response_model=VendorDetail)
def update_vendor(vendor_id: UUID, vendor_data: VendorUpdate, db: Session = Depends(get_db)):
    """Partial update - triggers async rescore"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    # Update fields
    update_data = vendor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)

    db.commit()
    db.refresh(vendor)

    # Trigger rescore
    score = score_vendor(vendor, triggered_by="manual")
    db.add(score)
    db.commit()

    return get_vendor(vendor.id, db)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(vendor_id: UUID, db: Session = Depends(get_db)):
    """Soft-delete (sets archived_at)"""
    from datetime import datetime

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    vendor.archived_at = datetime.utcnow()
    db.commit()

    return None


@router.post("/import", response_model=ImportResult)
async def import_vendors(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Multipart CSV upload (vendor_registry.csv shape)"""
    # Stub implementation - full CSV parsing to be implemented
    return ImportResult(
        rows_processed=0,
        rows_succeeded=0,
        rows_failed=0,
        errors=[]
    )


@router.get("/export.csv")
def export_vendors(db: Session = Depends(get_db)):
    """Export vendors as CSV"""
    # Stub - to be implemented
    return {"message": "CSV export not yet implemented"}
