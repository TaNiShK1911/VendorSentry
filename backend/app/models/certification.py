"""
Certification model — tracks SOC 2, ISO 27001, PCI-DSS etc.

Each row represents one certification on one vendor.
The cert-expiry watcher in services/monitoring/ reads this table.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Date, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

CERT_TYPES = (
    "SOC2_TYPE1",
    "SOC2_TYPE2",
    "ISO_27001",
    "PCI_DSS",
    "GDPR_COMPLIANCE",
    "HIPAA",
    "OTHER",
)
CERT_STATUSES = ("current", "expired", "pending_renewal", "unknown")
CERT_SOURCES = ("manual", "audit_report", "status_api", "csv_import")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    cert_type: Mapped[str] = mapped_column(
        SAEnum(*CERT_TYPES, name="cert_type_enum"), nullable=False
    )

    status: Mapped[str] = mapped_column(
        SAEnum(*CERT_STATUSES, name="cert_status_enum"), nullable=False, default="unknown"
    )

    issued_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Where this cert record came from
    source: Mapped[str] = mapped_column(
        SAEnum(*CERT_SOURCES, name="cert_source_enum"), nullable=False, default="manual"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="certifications")

    def __repr__(self) -> str:
        return (
            f"<Certification vendor_id={self.vendor_id!r} "
            f"type={self.cert_type!r} status={self.status!r} expiry={self.expiry_date}>"
        )
