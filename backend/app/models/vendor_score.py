"""
VendorScore model — one row per scoring event.

The most recent row for a vendor is its current score.
Previous rows form the risk-history timeline.

ARCHITECTURAL RULE: composite_score, tier, and status_color are
NEVER written directly by LLM output. They are always the result
of deterministic functions in services/scoring/engine.py.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VendorScore(Base):
    __tablename__ = "vendor_scores"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Four sub-scores (0–100 each)
    breach_subscore: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    access_subscore: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    compliance_subscore: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    financial_subscore: Mapped[float] = mapped_column(Float, nullable=False, default=40.0)

    # Composite score (0–100): weighted sum of the four sub-scores
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Tier and status color — always derived deterministically, never set by LLM
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    status_color: Mapped[str] = mapped_column(String(10), nullable=False)

    # Anomaly types detected during this scoring event
    anomaly_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # LLM-generated plain-English rationale
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # What caused this recompute
    triggered_by: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual",
    )

    # Link to the immediately preceding score
    previous_score_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("vendor_scores.id"), nullable=True
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="scores")
    previous_score: Mapped[Optional["VendorScore"]] = relationship(
        "VendorScore", remote_side="VendorScore.id", foreign_keys=[previous_score_id]
    )

    def __repr__(self) -> str:
        return (
            f"<VendorScore vendor_id={self.vendor_id!r} "
            f"composite={self.composite_score:.1f} tier={self.tier!r}>"
        )
