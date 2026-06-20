"""
BreachEvent model — one row per security breach associated with a vendor.

Source can be the breach-DB poller (monitored) or a manually logged incident.
The breach_subscore in the scoring engine reads all rows for a vendor and
applies recency decay: severity_weight * exp(-months_since / 12).
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Date, DateTime, Boolean, ForeignKey, Enum as SAEnum, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

BREACH_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
BREACH_SOURCES = ("breach_db", "manual", "public_records")


class BreachEvent(Base):
    __tablename__ = "breach_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    breach_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    severity: Mapped[str] = mapped_column(
        SAEnum(*BREACH_SEVERITIES, name="breach_severity_enum"), nullable=False
    )

    source: Mapped[str] = mapped_column(
        SAEnum(*BREACH_SOURCES, name="breach_source_enum"), nullable=False, default="manual"
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="breach_history")

    def __repr__(self) -> str:
        return (
            f"<BreachEvent vendor_id={self.vendor_id!r} "
            f"severity={self.severity!r} date={self.breach_date} resolved={self.resolved}>"
        )
