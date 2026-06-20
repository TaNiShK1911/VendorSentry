"""Alert deduplication logic"""
import hashlib
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Alert, AlertType


def generate_dedup_key(vendor_id: UUID, alert_type: AlertType, trigger_value: str = "") -> str:
    """
    Generate a unique dedup key for an alert.

    This prevents the same alert from firing multiple times for the same condition.
    Per AGENT.md, alerts must be deduped so they don't spam daily.
    """
    key_string = f"{vendor_id}:{alert_type.value}:{trigger_value}"
    return hashlib.sha256(key_string.encode()).hexdigest()


def check_alert_exists(db: Session, dedup_key: str) -> bool:
    """Check if an alert with this dedup_key already exists and is unresolved"""
    existing = db.query(Alert).filter(
        Alert.dedup_key == dedup_key,
        Alert.resolved_at.is_(None)
    ).first()
    return existing is not None


def should_create_alert(db: Session, vendor_id: UUID, alert_type: AlertType, trigger_value: str = "") -> Optional[str]:
    """
    Determine if an alert should be created.

    Returns the dedup_key if alert should be created, None otherwise.
    """
    dedup_key = generate_dedup_key(vendor_id, alert_type, trigger_value)

    if check_alert_exists(db, dedup_key):
        return None  # Alert already exists, skip

    return dedup_key
