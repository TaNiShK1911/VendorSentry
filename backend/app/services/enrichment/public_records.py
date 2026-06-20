"""Mocked adapter for public records enrichment."""
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Vendor, EvidenceSignal

@celery_app.task(name="app.services.enrichment.public_records.check_public_records")
def check_public_records():
    """
    Mocked adapter — real implementation requires a real data source.
    """
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
        signals_created = 0

        for vendor in vendors:
            # Deterministic mock based on the vendor's existing financial_health_signal
            base_signal = vendor.financial_health_signal or "stable"
            
            enrichment_data = {
                "financial_health_signal": base_signal,
                "regulatory_flags": []
            }
            
            signal = EvidenceSignal(
                vendor_id=vendor.id,
                source="public_records",
                signal_type="financial_update",
                payload=enrichment_data,
                received_at=datetime.utcnow()
            )
            db.add(signal)
            signals_created += 1

        db.commit()
        return f"Public records check complete: {signals_created} signals generated"
    finally:
        db.close()
