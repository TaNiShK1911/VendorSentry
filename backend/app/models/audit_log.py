"""
AuditLogEntry model — immutable append-only log of every change.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    change_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # JSON snapshots of before/after state
    before: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLogEntry {self.change_type!r} on "
            f"{self.entity_type!r}:{self.entity_id!r} by {self.actor!r}>"
        )
