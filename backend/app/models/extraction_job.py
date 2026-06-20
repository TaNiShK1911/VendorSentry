"""
ExtractionJob model — tracks one LLM extraction attempt per document upload.
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, JSON, Text, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DocumentType(str, Enum):
    """Document type enumeration for extraction jobs"""
    CSV_ROW = "csv_row"
    CONTRACT_PDF = "contract_pdf"
    SECURITY_ASSESSMENT = "security_assessment"
    AUDIT_REPORT = "audit_report"
    MANUAL_NOTE = "manual_note"


class ExtractionStatus(str, Enum):
    """Extraction job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Also accept document_type as alias
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Raw input
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Validated LLM output
    structured_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Confidence estimate from the LLM (0.0–1.0)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Conflict records
    flagged_conflicts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Alias for frontend compatibility
    conflicts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )

    # Error detail if status == "failed"
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="extraction_jobs")

    def __repr__(self) -> str:
        return (
            f"<ExtractionJob id={self.id!r} vendor_id={self.vendor_id!r} "
            f"type={self.source_type!r} status={self.status!r}>"
        )
