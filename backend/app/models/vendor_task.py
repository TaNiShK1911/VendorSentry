from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.models.base import Base

class VendorTask(Base):
    __tablename__ = "vendor_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    task_type = Column(String, default="onboarding")  # e.g., 'onboarding', 'remediation'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = relationship("Vendor", backref="tasks")
