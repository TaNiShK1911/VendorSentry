"""
EvidenceSignal model — the unifying table for non-document external signals.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EvidenceSignal(Base):
    __tablename__ = "evidence_signals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source: Mapped[str] = mapped_column(String(50), nullable=False)

    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Raw signal payload exactly as received from the external source
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    received_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Set once this signal has triggered a VendorScore computation
    consumed_by_score_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("vendor_scores.id"), nullable=True
    )

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="evidence_signals")

    def __repr__(self) -> str:
        return (
            f"<EvidenceSignal vendor_id={self.vendor_id!r} "
            f"source={self.source!r} type={self.signal_type!r}>"
        )
