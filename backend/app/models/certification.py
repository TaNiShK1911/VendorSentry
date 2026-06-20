"""
Certification model — tracks SOC 2, ISO 27001, PCI-DSS etc.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    cert_type: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")

    issued_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Where this cert record came from
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="certifications")

    def __repr__(self) -> str:
        return (
            f"<Certification vendor_id={self.vendor_id!r} "
            f"type={self.cert_type!r} status={self.status!r} expiry={self.expiry_date}>"
        )
