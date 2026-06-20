"""
Vendor model — the primary entity in VendorSentry.

Each Vendor represents one third-party supplier. The risk profile
(certifications, breach history, data access scope, current score)
is stored in related tables to keep this table lean and queryable.
"""
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Numeric, Date, DateTime, Enum as SAEnum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

# Vendor types per the problem statement taxonomy
VENDOR_TYPES = (
    "cloud_provider",
    "contractor",
    "mss_provider",
    "payment_processor",
    "software_vendor",
    "other",
)

CONTRACT_STATUSES = ("active", "expired", "terminated", "pending")

FINANCIAL_HEALTH_SIGNALS = ("stable", "watch", "distressed", "unknown")

FINANCIAL_HEALTH_SOURCES = ("public_records_enrichment", "manual", "unknown")


class Vendor(Base):
    __tablename__ = "vendors"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vendor_type: Mapped[str] = mapped_column(
        SAEnum(*VENDOR_TYPES, name="vendor_type_enum"),
        nullable=False,
        default="other",
    )

    # Contact info — stored as JSON for flexibility (liaison_name, email, phone)
    contact: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Financial
    annual_spend: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    # Contract dates
    contract_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_status: Mapped[Optional[str]] = mapped_column(
        SAEnum(*CONTRACT_STATUSES, name="contract_status_enum"), nullable=True
    )

    # Financial health (derived from enrichment adapter)
    financial_health_signal: Mapped[str] = mapped_column(
        SAEnum(*FINANCIAL_HEALTH_SIGNALS, name="financial_health_signal_enum"),
        nullable=False,
        default="unknown",
    )
    financial_health_source: Mapped[str] = mapped_column(
        SAEnum(*FINANCIAL_HEALTH_SOURCES, name="financial_health_source_enum"),
        nullable=False,
        default="unknown",
    )

    # Flags for monitoring
    under_investigation: Mapped[bool] = mapped_column(default=False)

    # Assessment tracking
    last_assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft-delete: excluded from default queries when set
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships (lazy-loaded by default; eager-load in queries as needed)
    certifications: Mapped[list["Certification"]] = relationship(
        "Certification", back_populates="vendor", cascade="all, delete-orphan"
    )
    breach_history: Mapped[list["BreachEvent"]] = relationship(
        "BreachEvent", back_populates="vendor", cascade="all, delete-orphan"
    )
    data_access_scope: Mapped[Optional["DataAccessScope"]] = relationship(
        "DataAccessScope", back_populates="vendor", uselist=False, cascade="all, delete-orphan"
    )
    scores: Mapped[list["VendorScore"]] = relationship(
        "VendorScore", back_populates="vendor", cascade="all, delete-orphan",
        order_by="VendorScore.computed_at.desc()"
    )
    extraction_jobs: Mapped[list["ExtractionJob"]] = relationship(
        "ExtractionJob", back_populates="vendor", cascade="all, delete-orphan"
    )
    evidence_signals: Mapped[list["EvidenceSignal"]] = relationship(
        "EvidenceSignal", back_populates="vendor", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="vendor", cascade="all, delete-orphan"
    )


    def __repr__(self) -> str:
        return f"<Vendor id={self.id!r} name={self.name!r}>"
