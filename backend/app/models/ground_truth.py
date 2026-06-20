"""
GroundTruth model — evaluation-only table from vendor_labels.csv.

CRITICAL ARCHITECTURAL RULE: This table is NEVER read by the live
scoring engine. It is loaded by seed.py and read only by evaluate.py.
Keeping ground truth isolated prevents circular scoring (leaking the
answer key into the live system).
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class GroundTruth(Base):
    __tablename__ = "ground_truth"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # vendor_id from vendor_registry.csv (may or may not have a live Vendor row)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Core ground-truth fields from vendor_labels.csv
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anomaly_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Expired certs as listed in labels (JSON array of cert type strings)
    expired_certifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Human-readable explanation from the labels CSV
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<GroundTruth vendor={self.vendor_name!r} "
            f"anomaly={self.is_anomaly} severity={self.severity!r}>"
        )
