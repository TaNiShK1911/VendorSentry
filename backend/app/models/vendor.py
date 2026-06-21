"""
Vendor model — the primary entity in VendorSentry.

Each Vendor represents one third-party supplier. The risk profile
(certifications, breach history, data access scope, current score)
is stored in related tables to keep this table lean and queryable.
"""
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Numeric, Date, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Primary key — String(36) for SQLite + PostgreSQL compatibility
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vendor_type: Mapped[str] = mapped_column(
        String(50),
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
        String(50), nullable=True
    )

    # Financial health (derived from enrichment adapter)
    financial_health_signal: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )
    financial_health_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )

    # Flags for monitoring
    under_investigation: Mapped[bool] = mapped_column(default=False)

    # Domain for breach matching (lowercase, no scheme/path — e.g. "acmecloud.com")
    website_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Assessment tracking
    last_assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Soft-delete: excluded from default queries when set
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
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

    # Convenience properties for accessing contact fields
    @property
    def contact_name(self) -> Optional[str]:
        if self.contact and isinstance(self.contact, dict):
            return self.contact.get("liaison_name")
        return None

    @property
    def contact_email(self) -> Optional[str]:
        if self.contact and isinstance(self.contact, dict):
            return self.contact.get("email")
        return None

    def __repr__(self) -> str:
        return f"<Vendor id={self.id!r} name={self.name!r}>"
