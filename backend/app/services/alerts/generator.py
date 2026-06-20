"""Alert generation logic"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Alert, AlertType, AlertSeverity
from app.services.alerts.dedup import should_create_alert


def create_alert(
    db: Session,
    vendor_id: UUID,
    vendor_name: str,
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
    trigger_value: str = ""
) -> Optional[Alert]:
    """
    Create an alert if it doesn't already exist (dedup check).

    Returns the created alert or None if skipped due to dedup.
    """
    dedup_key = should_create_alert(db, vendor_id, alert_type, trigger_value)

    if not dedup_key:
        return None  # Alert already exists

    alert = Alert(
        vendor_id=vendor_id,
        type=alert_type,
        severity=severity,
        message=message,
        dedup_key=dedup_key,
        created_at=datetime.utcnow()
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert


def create_cert_expiring_alert(
    db: Session,
    vendor_id: UUID,
    vendor_name: str,
    cert_type: str,
    days_until_expiry: int
) -> Optional[Alert]:
    """Create cert expiring alert"""
    severity = AlertSeverity.HIGH if days_until_expiry <= 30 else AlertSeverity.MEDIUM
    message = f"{cert_type} certification expires in {days_until_expiry} days"

    return create_alert(
        db,
        vendor_id,
        vendor_name,
        AlertType.CERT_EXPIRING,
        severity,
        message,
        trigger_value=f"{cert_type}:{days_until_expiry}"
    )


def create_contract_expiring_alert(
    db: Session,
    vendor_id: UUID,
    vendor_name: str,
    days_until_expiry: int
) -> Optional[Alert]:
    """Create contract expiring alert"""
    severity = AlertSeverity.MEDIUM
    message = f"Contract expires in {days_until_expiry} days"

    return create_alert(
        db,
        vendor_id,
        vendor_name,
        AlertType.CONTRACT_EXPIRING,
        severity,
        message,
        trigger_value=str(days_until_expiry)
    )


def create_assessment_overdue_alert(
    db: Session,
    vendor_id: UUID,
    vendor_name: str,
    days_overdue: int
) -> Optional[Alert]:
    """Create assessment overdue alert"""
    severity = AlertSeverity.MEDIUM
    message = f"Security assessment is {days_overdue} days overdue (>12 months since last review)"

    return create_alert(
        db,
        vendor_id,
        vendor_name,
        AlertType.ASSESSMENT_OVERDUE,
        severity,
        message,
        trigger_value=str(days_overdue)
    )


def create_new_breach_alert(
    db: Session,
    vendor_id: UUID,
    vendor_name: str,
    breach_description: str
) -> Optional[Alert]:
    """Create new breach detected alert"""
    severity = AlertSeverity.CRITICAL
    message = f"New breach detected: {breach_description}"

    return create_alert(
        db,
        vendor_id,
        vendor_name,
        AlertType.NEW_BREACH,
        severity,
        message,
        trigger_value=breach_description[:50]
    )


def create_score_tier_changed_alert(
    db: Session,
    vendor_id: UUID,
    vendor_name: str,
    old_tier: str,
    new_tier: str,
    reason: str
) -> Optional[Alert]:
    """Create score tier changed alert"""
    # Determine severity based on new tier
    if new_tier in ["CRITICAL", "HIGH"]:
        severity = AlertSeverity.HIGH
    else:
        severity = AlertSeverity.MEDIUM

    message = f"Risk tier changed {old_tier} → {new_tier} following {reason}"

    return create_alert(
        db,
        vendor_id,
        vendor_name,
        AlertType.SCORE_TIER_CHANGED,
        severity,
        message,
        trigger_value=f"{old_tier}:{new_tier}"
    )
