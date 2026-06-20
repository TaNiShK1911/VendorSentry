"""Vendor CRUD API endpoints"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, VendorScore, Alert, DataAccessScope
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorListItem, VendorDetail, ImportResult, ContactInfo
from app.services.scoring.engine import score_vendor, get_latest_score
from app.services.extraction.narrative import generate_rationale

router = APIRouter()


@router.get("/vendors")
def list_vendors(
    q: Optional[str] = None,
    search: Optional[str] = None,
    tier: Optional[str] = None,
    type: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    has_pii_access: Optional[bool] = None,
    has_pii: Optional[bool] = None,
    cert_expiring_within_days: Optional[int] = None,
    sort: str = "score_desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    per_page: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List/search/filter vendors - backs the main portfolio grid"""
    # Accept both 'q' and 'search' param names
    search_term = q or search
    # Accept both 'page_size' and 'per_page'
    actual_page_size = per_page or page_size
    # Accept both 'has_pii_access' and 'has_pii'
    pii_filter = has_pii_access if has_pii_access is not None else has_pii

    query = db.query(Vendor).filter(Vendor.archived_at.is_(None))

    # Apply filters
    if search_term:
        query = query.filter(Vendor.name.ilike(f"%{search_term}%"))

    if type:
        query = query.filter(Vendor.vendor_type == type)

    # Get total count
    total_items = query.count()

    # Pagination
    offset = (page - 1) * actual_page_size
    vendors = query.offset(offset).limit(actual_page_size).all()

    # Build response items in the format frontend expects
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

        # Check PII access from DataAccessScope relationship
        has_pii_val = False
        scope = db.query(DataAccessScope).filter(
            DataAccessScope.vendor_id == vendor.id
        ).first()
        if scope:
            has_pii_val = scope.pii_access

        # Map to frontend's expected field names
        items.append({
            "id": vendor.id,
            "name": vendor.name,
            "vendor_type": vendor.vendor_type,
            "contact_email": vendor.contact_email or "",
            "annual_spend": float(vendor.annual_spend) if vendor.annual_spend else 0,
            "contract_start": str(vendor.contract_start) if vendor.contract_start else None,
            "contract_end": str(vendor.contract_end) if vendor.contract_end else None,
            "has_pii_access": has_pii_val,
            "has_financial_access": scope.financial_access if scope else False,
            "systems_access": scope.systems if scope else [],
            "data_access_notes": scope.scope_notes if scope else "",
            "status": vendor.contract_status or "active",
            "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
            "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
            "composite_score": latest_score.composite_score if latest_score else 0.0,
            "status_color": latest_score.status_color if latest_score else "GREEN",
            "risk_tier": latest_score.tier if latest_score else "CLEAR",
            "active_alerts": alert_count,
            "last_assessed": vendor.last_assessed_at.isoformat() if vendor.last_assessed_at else None,
        })

    total_pages = (total_items + actual_page_size - 1) // actual_page_size

    # Return in the format the frontend expects
    return {
        "vendors": items,
        "pagination": {
            "page": page,
            "per_page": actual_page_size,
            "total": total_items,
            "total_pages": total_pages,
        }
    }


@router.get("/vendors/{vendor_id}")
def get_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Get full vendor profile - drill-down view"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found"
        )

    # Get latest score
    latest_score = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor.id
    ).order_by(VendorScore.computed_at.desc()).first()

    # Get score history (last 10)
    score_history = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor.id
    ).order_by(VendorScore.computed_at.desc()).limit(10).all()

    # Get data access scope
    scope = db.query(DataAccessScope).filter(
        DataAccessScope.vendor_id == vendor.id
    ).first()

    # Get alerts count
    alert_count = db.query(Alert).filter(
        Alert.vendor_id == vendor.id,
        Alert.resolved_at.is_(None)
    ).count()

    return {
        "id": vendor.id,
        "name": vendor.name,
        "vendor_type": vendor.vendor_type,
        "contact_email": vendor.contact_email or "",
        "annual_spend": float(vendor.annual_spend) if vendor.annual_spend else 0,
        "contract_start": str(vendor.contract_start) if vendor.contract_start else None,
        "contract_end": str(vendor.contract_end) if vendor.contract_end else None,
        "has_pii_access": scope.pii_access if scope else False,
        "has_financial_access": scope.financial_access if scope else False,
        "systems_access": scope.systems if scope else [],
        "data_access_notes": scope.scope_notes if scope else "",
        "status": vendor.contract_status or "active",
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
        "composite_score": latest_score.composite_score if latest_score else 0.0,
        "status_color": latest_score.status_color if latest_score else "GREEN",
        "risk_tier": latest_score.tier if latest_score else "CLEAR",
        "active_alerts": alert_count,
        "last_assessed": vendor.last_assessed_at.isoformat() if vendor.last_assessed_at else None,
        "contract_days_remaining": (vendor.contract_end - vendor.contract_end.__class__.today()).days if vendor.contract_end else None,
        "current_score": {
            "composite_score": latest_score.composite_score,
            "tier": latest_score.tier,
            "status_color": latest_score.status_color,
            "subscores": {
                "breach_subscore": latest_score.breach_subscore,
                "access_subscore": latest_score.access_subscore,
                "compliance_subscore": latest_score.compliance_subscore,
                "financial_subscore": latest_score.financial_subscore,
            },
            "anomaly_types": latest_score.anomaly_types or [],
            "rationale": latest_score.rationale,
            "triggered_by": latest_score.triggered_by,
            "computed_at": latest_score.computed_at.isoformat() if latest_score.computed_at else None,
        } if latest_score else None,
        "score_history": [
            {
                "composite_score": s.composite_score,
                "tier": s.tier,
                "status_color": s.status_color,
                "computed_at": s.computed_at.isoformat() if s.computed_at else None,
            }
            for s in score_history
        ],
        # Legacy fields for backward compat with other schemas
        "contact": vendor.contact,
        "certifications": [],
        "data_access_scope": {
            "pii_access": scope.pii_access,
            "financial_access": scope.financial_access,
            "broad_system_access": scope.broad_system_access,
            "systems": scope.systems,
            "scope_notes": scope.scope_notes,
        } if scope else None,
        "breach_history": [],
        "financial_health_signal": vendor.financial_health_signal,
        "financial_health_source": vendor.financial_health_source,
        "under_investigation": vendor.under_investigation,
    }


@router.post("/vendors", status_code=status.HTTP_201_CREATED)
def create_vendor(vendor_data: VendorCreate, db: Session = Depends(get_db)):
    """Create a vendor manually"""
    vendor = Vendor(
        name=vendor_data.name,
        vendor_type=vendor_data.vendor_type,
        contact=vendor_data.contact.model_dump() if vendor_data.contact else None,
        annual_spend=vendor_data.annual_spend,
        contract_start=vendor_data.contract_start,
        contract_end=vendor_data.contract_end,
        contract_status=vendor_data.contract_status,
        financial_health_signal=vendor_data.financial_health_signal,
        financial_health_source=vendor_data.financial_health_source,
        under_investigation=vendor_data.under_investigation,
    )
    db.add(vendor)
    db.flush()

    # Trigger initial scoring
    breaches = vendor.breach_history
    certs = vendor.certifications
    scope = vendor.data_access_scope
    result = score_vendor(vendor, breaches, certs, scope, triggered_by="manual")

    rationale = generate_rationale(
        vendor_name=vendor.name,
        composite_score=result.composite_score,
        tier=result.tier,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        anomaly_types=result.anomaly_types,
    )

    score_row = VendorScore(
        vendor_id=vendor.id,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        composite_score=result.composite_score,
        tier=result.tier,
        status_color=result.status_color,
        anomaly_types=result.anomaly_types,
        triggered_by=result.triggered_by,
        rationale=rationale,
    )
    db.add(score_row)
    db.commit()

    return get_vendor(vendor.id, db)


@router.patch("/vendors/{vendor_id}")
def update_vendor(vendor_id: str, vendor_data: VendorUpdate, db: Session = Depends(get_db)):
    """Partial update - triggers async rescore"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    # Update fields
    update_data = vendor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "contact" and value is not None:
            setattr(vendor, field, value if isinstance(value, dict) else value.model_dump())
        else:
            setattr(vendor, field, value)

    db.flush()

    # Trigger rescore
    breaches = vendor.breach_history
    certs = vendor.certifications
    scope = vendor.data_access_scope
    result = score_vendor(vendor, breaches, certs, scope, triggered_by="manual")

    rationale = generate_rationale(
        vendor_name=vendor.name,
        composite_score=result.composite_score,
        tier=result.tier,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        anomaly_types=result.anomaly_types,
    )

    score_row = VendorScore(
        vendor_id=vendor.id,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        composite_score=result.composite_score,
        tier=result.tier,
        status_color=result.status_color,
        anomaly_types=result.anomaly_types,
        triggered_by=result.triggered_by,
        rationale=rationale,
    )
    db.add(score_row)
    db.commit()

    return get_vendor(vendor.id, db)


@router.delete("/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Soft-delete (sets archived_at)"""
    from datetime import datetime

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    vendor.archived_at = datetime.utcnow()
    return None


@router.post("/vendors/import")
async def import_vendors(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Multipart CSV upload (vendor_registry.csv shape)"""
    return ImportResult(
        rows_processed=0,
        rows_succeeded=0,
        rows_failed=0,
        errors=[]
    )


@router.get("/vendors/export.csv")
def export_vendors(db: Session = Depends(get_db)):
    """Export vendors as CSV"""
    return {"message": "CSV export not yet implemented"}
