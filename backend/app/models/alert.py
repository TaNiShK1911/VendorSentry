"""
Alert model for monitoring and notifications.

Alerts are deduped to prevent spam — see app/services/alerts/dedup.py
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AlertType(str, Enum):
    """Alert type enumeration"""
    CERT_EXPIRING = "CERT_EXPIRING"
    CONTRACT_EXPIRING = "CONTRACT_EXPIRING"
    ASSESSMENT_OVERDUE = "ASSESSMENT_OVERDUE"
    NEW_BREACH = "NEW_BREACH"
    SCORE_TIER_CHANGED = "SCORE_TIER_CHANGED"


class AlertSeverity(str, Enum):
    """Alert severity enumeration"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    type: Mapped[str] = mapped_column(String(50), nullable=False)

    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert id={self.id!r} type={self.type!r} vendor_id={self.vendor_id!r}>"
