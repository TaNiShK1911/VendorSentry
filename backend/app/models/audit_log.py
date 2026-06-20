"""
AuditLogEntry model — immutable append-only log of every change.

Records who changed what on which entity, with before/after snapshots.
Used for compliance evidence: GDPR Art. 28, NIST SA-9 audit trails.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

ENTITY_TYPES = ("vendor", "vendor_score", "certification", "breach_event", "alert")
CHANGE_TYPES = (
    "created",
    "updated",
    "deleted",
    "score_computed",
    "alert_generated",
    "extraction_completed",
    "evidence_received",
)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    change_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # JSON snapshots of before/after state (None for creations/deletions)
    before: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # "system" for automated actions; user id/email for manual
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLogEntry {self.change_type!r} on "
            f"{self.entity_type!r}:{self.entity_id!r} by {self.actor!r}>"
        )
