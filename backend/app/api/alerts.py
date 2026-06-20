"""Alerts API endpoints"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Alert, Vendor, AlertType, AlertSeverity
from app.schemas import AlertResponse, AlertSummary, AlertResolve, PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def list_alerts(
    status_filter: str = Query("open", alias="status"),
    severity: Optional[AlertSeverity] = None,
    vendor_id: Optional[UUID] = None,
    type: Optional[AlertType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List/filter alerts"""
    query = db.query(Alert).join(Vendor)

    # Apply status filter
    if status_filter == "open":
        query = query.filter(Alert.resolved_at.is_(None))
    elif status_filter == "acknowledged":
        query = query.filter(
            Alert.acknowledged_at.isnot(None),
            Alert.resolved_at.is_(None)
        )
    elif status_filter == "resolved":
        query = query.filter(Alert.resolved_at.isnot(None))

    # Apply other filters
    if severity:
        query = query.filter(Alert.severity == severity)

    if vendor_id:
        query = query.filter(Alert.vendor_id == vendor_id)

    if type:
        query = query.filter(Alert.type == type)

    # Get total count
    total_items = query.count()

    # Pagination
    offset = (page - 1) * page_size
    alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(page_size).all()

    # Build response items
    items = []
    for alert in alerts:
        vendor = db.query(Vendor).filter(Vendor.id == alert.vendor_id).first()
        items.append(AlertResponse(
            id=alert.id,
            vendor_id=alert.vendor_id,
            vendor_name=vendor.name if vendor else "Unknown",
            type=alert.type,
            severity=alert.severity,
            message=alert.message,
            created_at=alert.created_at,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at
        ))

    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: UUID, db: Session = Depends(get_db)):
    """Acknowledge an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)

    vendor = db.query(Vendor).filter(Vendor.id == alert.vendor_id).first()

    return AlertResponse(
        id=alert.id,
        vendor_id=alert.vendor_id,
        vendor_name=vendor.name if vendor else "Unknown",
        type=alert.type,
        severity=alert.severity,
        message=alert.message,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at
    )


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: UUID, data: AlertResolve, db: Session = Depends(get_db)):
    """Resolve an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.resolved_at = datetime.utcnow()
    if data.resolution_note:
        alert.resolution_note = data.resolution_note

    db.commit()
    db.refresh(alert)

    vendor = db.query(Vendor).filter(Vendor.id == alert.vendor_id).first()

    return AlertResponse(
        id=alert.id,
        vendor_id=alert.vendor_id,
        vendor_name=vendor.name if vendor else "Unknown",
        type=alert.type,
        severity=alert.severity,
        message=alert.message,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at
    )


@router.get("/summary", response_model=AlertSummary)
def get_alert_summary(db: Session = Depends(get_db)):
    """Badge/counter widget for nav bar"""
    open_critical = db.query(Alert).filter(
        Alert.resolved_at.is_(None),
        Alert.severity == AlertSeverity.CRITICAL
    ).count()

    open_high = db.query(Alert).filter(
        Alert.resolved_at.is_(None),
        Alert.severity == AlertSeverity.HIGH
    ).count()

    open_total = db.query(Alert).filter(
        Alert.resolved_at.is_(None)
    ).count()

    return AlertSummary(
        open_critical=open_critical,
        open_high=open_high,
        open_total=open_total
    )
