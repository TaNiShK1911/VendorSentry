"""
Initialize database with sample data for development/demo.
Run: python -m scripts.init_db
"""
import sys
import os
import uuid
from datetime import datetime, date, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, SessionLocal
from app.models.vendor import Vendor
from pathlib import Path
from app.models.vendor_score import VendorScore
from app.models.certification import Certification
from app.models.breach import BreachEvent
from app.models.data_access import DataAccessScope
from app.models.alert import Alert
from app.models.evidence_signal import EvidenceSignal
from app.models.audit_log import AuditLogEntry
from app.models.ground_truth import GroundTruth
from app.models.extraction_job import ExtractionJob


def reset_and_seed():
    db = SessionLocal()
    print("Wiping existing vendors...")
    db.query(Vendor).delete()
    db.commit()
    print("Database wiped.")

    _REPO_ROOT = Path(__file__).resolve().parents[2]
    data_dir = _REPO_ROOT / "backend" / "sample_data"
    
    # Also support running via Docker
    if not data_dir.exists():
        data_dir = Path("/app/sample_data")
        
    registry_csv = data_dir / "vendor_registry.csv"
    labels_csv   = data_dir / "vendor_labels.csv"
    
    if not registry_csv.exists():
        print(f"Error: {registry_csv} not found")
        sys.exit(1)
        
    print(f"Loading CSV from {registry_csv}...")
    from scripts.seed import load_vendor_registry
    
    # Clear alerts, ground truth etc.
    from app.models.alert import Alert
    from app.models.ground_truth import GroundTruth
    db.query(Alert).delete()
    db.query(GroundTruth).delete()
    db.commit()

    reg_processed, reg_ok, reg_errors = load_vendor_registry(registry_csv, db)
    db.commit()
    
    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print(f"  Registry : {reg_ok}/{reg_processed} rows loaded  ({len(reg_errors)} errors)")
    print("=" * 60)

from app.models.base import Base
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    reset_and_seed()
