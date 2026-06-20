"""
EvidenceSignal model — the unifying table for non-document external signals.

Every signal from the breach-DB poller, the public-records enrichment
adapter, or the third-party status-check API lands here first.
The monitoring sweep then processes each signal: updates vendor fields
and triggers a rescore via services/scoring/engine.py.

This separates document-driven extraction (ExtractionJob) from
event-driven external signals (EvidenceSignal) while feeding both
into the same scoring engine.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

SIGNAL_SOURCES = ("breach_db", "public_records", "status_api", "extraction_job")
SIGNAL_TYPES = (
    "new_breach",
    "financial_health_change",
    "cert_status_change",
    "regulatory_action",
)


class EvidenceSignal(Base):
    __tablename__ = "evidence_signals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source: Mapped[str] = mapped_column(
        SAEnum(*SIGNAL_SOURCES, name="evidence_source_enum"), nullable=False
    )

    signal_type: Mapped[str] = mapped_column(
        SAEnum(*SIGNAL_TYPES, name="signal_type_enum"), nullable=False
    )

    # Raw signal payload exactly as received from the external source
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Set once this signal has triggered a VendorScore computation
    consumed_by_score_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("vendor_scores.id"), nullable=True
    )

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="evidence_signals")

    def __repr__(self) -> str:
        return (
            f"<EvidenceSignal vendor_id={self.vendor_id!r} "
            f"source={self.source!r} type={self.signal_type!r}>"
        )
