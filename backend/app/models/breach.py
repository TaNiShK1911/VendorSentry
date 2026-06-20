"""
BreachEvent model — one row per security breach associated with a vendor.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Date, DateTime, Boolean, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BreachEvent(Base):
    __tablename__ = "breach_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    breach_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="breach_history")

    def __repr__(self) -> str:
        return (
            f"<BreachEvent vendor_id={self.vendor_id!r} "
            f"severity={self.severity!r} date={self.breach_date} resolved={self.resolved}>"
        )
