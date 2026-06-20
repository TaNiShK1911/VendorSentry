"""Alerts API endpoints"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Alert, Vendor, AlertType, AlertSeverity

router = APIRouter()


@router.get("/alerts")
def list_alerts(
    status_filter: str = Query("open", alias="status"),
    severity: Optional[str] = None,
    vendor_id: Optional[str] = None,
    type: Optional[str] = None,
    alert_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    per_page: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List/filter alerts"""
    actual_page_size = per_page or page_size
    # Accept both 'type' and 'alert_type'
    type_filter = type or alert_type

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
        query = query.filter(Alert.severity == severity.upper())

    if vendor_id:
        query = query.filter(Alert.vendor_id == vendor_id)

    if type_filter:
        query = query.filter(Alert.type == type_filter)

    # Get total count
    total_items = query.count()

    # Pagination
    offset = (page - 1) * actual_page_size
    alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(actual_page_size).all()

    # Build response items matching frontend Alert interface
    items = []
    for alert in alerts:
        vendor = db.query(Vendor).filter(Vendor.id == alert.vendor_id).first()

        # Derive status from timestamps
        if alert.resolved_at:
            alert_status = "resolved"
        elif alert.acknowledged_at:
            alert_status = "acknowledged"
        else:
            alert_status = "open"

        items.append({
            "id": alert.id,
            "vendor_id": alert.vendor_id,
            "vendor_name": vendor.name if vendor else "Unknown",
            "alert_type": alert.type,
            "severity": alert.severity.lower() if alert.severity else "medium",
            "status": alert_status,
            "title": alert.message[:80] if alert.message else "",
            "message": alert.message,
            "metadata": {},
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        })

    total_pages = (total_items + actual_page_size - 1) // actual_page_size

    # Return in frontend's expected format
    return {
        "alerts": items,
        "pagination": {
            "page": page,
            "per_page": actual_page_size,
            "total": total_items,
            "total_pages": total_pages,
        }
    }


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    """Acknowledge an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.acknowledged_at = datetime.utcnow()
    db.commit()

    vendor = db.query(Vendor).filter(Vendor.id == alert.vendor_id).first()

    return {
        "id": alert.id,
        "vendor_id": alert.vendor_id,
        "vendor_name": vendor.name if vendor else "Unknown",
        "alert_type": alert.type,
        "severity": alert.severity.lower() if alert.severity else "medium",
        "status": "acknowledged",
        "title": alert.message[:80] if alert.message else "",
        "message": alert.message,
        "metadata": {},
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "resolved_at": None,
    }


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    """Resolve an alert — body is optional"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.resolved_at = datetime.utcnow()
    db.commit()

    vendor = db.query(Vendor).filter(Vendor.id == alert.vendor_id).first()

    return {
        "id": alert.id,
        "vendor_id": alert.vendor_id,
        "vendor_name": vendor.name if vendor else "Unknown",
        "alert_type": alert.type,
        "severity": alert.severity.lower() if alert.severity else "medium",
        "status": "resolved",
        "title": alert.message[:80] if alert.message else "",
        "message": alert.message,
        "metadata": {},
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }


@router.get("/alerts/summary")
def get_alert_summary(db: Session = Depends(get_db)):
    """Badge/counter widget for nav bar — returns full summary matching frontend AlertSummary type"""
    # Count by severity
    open_critical = db.query(Alert).filter(
        Alert.resolved_at.is_(None),
        Alert.severity == "CRITICAL"
    ).count()

    open_high = db.query(Alert).filter(
        Alert.resolved_at.is_(None),
        Alert.severity == "HIGH"
    ).count()

    open_medium = db.query(Alert).filter(
        Alert.resolved_at.is_(None),
        Alert.severity == "MEDIUM"
    ).count()

    open_low = db.query(Alert).filter(
        Alert.resolved_at.is_(None),
        Alert.severity == "LOW"
    ).count()

    open_total = open_critical + open_high + open_medium + open_low

    # Count by type
    by_type = {}
    for at in ["CERT_EXPIRING", "CONTRACT_EXPIRING", "ASSESSMENT_OVERDUE", "NEW_BREACH", "SCORE_TIER_CHANGED"]:
        by_type[at] = db.query(Alert).filter(
            Alert.resolved_at.is_(None),
            Alert.type == at
        ).count()

    return {
        "total_open": open_total,
        "by_severity": {
            "critical": open_critical,
            "high": open_high,
            "medium": open_medium,
            "low": open_low,
        },
        "by_type": by_type,
        "recent_alerts": open_total,
        "trend": "stable",
    }
