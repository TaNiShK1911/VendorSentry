"""
VendorSentry SQLAlchemy models package.
Import all models here so Alembic can auto-detect them.
"""
from app.models.vendor import Vendor
from app.models.vendor_score import VendorScore
from app.models.certification import Certification
from app.models.breach import BreachEvent
from app.models.data_access import DataAccessScope
from app.models.extraction_job import ExtractionJob
from app.models.evidence_signal import EvidenceSignal
from app.models.audit_log import AuditLogEntry
from app.models.ground_truth import GroundTruth

__all__ = [
    "Vendor",
    "VendorScore",
    "Certification",
    "BreachEvent",
    "DataAccessScope",
    "ExtractionJob",
    "EvidenceSignal",
    "AuditLogEntry",
    "GroundTruth",
]
