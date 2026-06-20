"""Mocked adapter for third-party status API integrations."""
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Vendor, EvidenceSignal
from app.services.extraction.conflict_checker import check_conflicts

@celery_app.task(name="app.services.integrations.status_api.check_live_cert_status")
def check_live_cert_status():
    """
    Mocked adapter — real implementation requires a real data source.
    """
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
        signals_created = 0

        for vendor in vendors:
            # Generate a mock API response
            api_response = {
                "compliance_claims": [
                    {
                        "type": c.cert_type,
                        "claimed_status": c.status,
                        "claimed_expiry": c.expiry_date.strftime("%Y-%m-%d") if c.expiry_date else None
                    } for c in vendor.certifications
                ]
            }

            # Check for conflicts using the existing conflict_checker logic
            conflicts = check_conflicts(
                extracted=api_response,
                existing_certs=vendor.certifications or [],
                existing_scope=vendor.data_access_scope
            )

            if conflicts:
                payload = {
                    "conflicts": [c.model_dump() for c in conflicts]
                }
                signal = EvidenceSignal(
                    vendor_id=vendor.id,
                    source="status_api",
                    signal_type="cert_conflict",
                    payload=payload,
                    received_at=datetime.utcnow()
                )
                db.add(signal)
                signals_created += 1

        db.commit()
        return f"Status API check complete: {signals_created} conflict signals generated"
    finally:
        db.close()
