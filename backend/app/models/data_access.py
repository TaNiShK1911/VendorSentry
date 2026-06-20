"""
DataAccessScope model — what data and systems a vendor can access.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DataAccessScope(Base):
    __tablename__ = "data_access_scopes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    vendor_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Sensitivity flags — drive the access_subscore formula
    pii_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    financial_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    broad_system_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Named systems (list of strings stored as JSON array)
    systems: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Free-text notes
    scope_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="data_access_scope")

    def __repr__(self) -> str:
        return (
            f"<DataAccessScope vendor_id={self.vendor_id!r} "
            f"pii={self.pii_access} financial={self.financial_access} "
            f"broad={self.broad_system_access}>"
        )
