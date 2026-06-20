"""
ExtractionJob model — tracks one LLM extraction attempt per document upload.

source_type tells the extraction service which prompt template to use:
  - csv_row           → structured CSV field parsing (no LLM needed)
  - contract_pdf      → data access, SLAs, compliance requirements extraction
  - security_assessment → Q&A-style questionnaire extraction
  - audit_report      → SOC 2 / ISO 27001 / PCI-DSS report summarization
  - manual_note       → freeform note from user

ARCHITECTURAL RULE: structured_output NEVER contains composite_score or tier.
The LLM only outputs data_access, compliance_claims, sla_terms, and conflicts.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum as SAEnum, Text, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

SOURCE_TYPES = (
    "csv_row",
    "contract_pdf",
    "security_assessment",
    "audit_report",
    "manual_note",
)

JOB_STATUSES = ("pending", "processing", "done", "failed")


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_type: Mapped[str] = mapped_column(
        SAEnum(*SOURCE_TYPES, name="extraction_source_type_enum"), nullable=False
    )

    # Raw input (truncated if very large — full text stored in file system if needed)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Validated LLM output — schema: {data_access, compliance_claims, sla_terms, conflicts: []}
    # NEVER contains composite_score or tier — those are computed separately
    structured_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Confidence estimate from the LLM (0.0–1.0) — informational only
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Conflict records — disagreements between LLM assertions and structured DB fields
    # Schema: [{field, claimed, actual_on_record, note}]
    flagged_conflicts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    status: Mapped[str] = mapped_column(
        SAEnum(*JOB_STATUSES, name="extraction_job_status_enum"),
        nullable=False,
        default="pending",
    )

    # Error detail if status == "failed"
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="extraction_jobs")

    def __repr__(self) -> str:
        return (
            f"<ExtractionJob id={self.id!r} vendor_id={self.vendor_id!r} "
            f"type={self.source_type!r} status={self.status!r}>"
        )
