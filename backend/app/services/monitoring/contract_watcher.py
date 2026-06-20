"""Contract expiry monitoring sweep (Celery task)"""
from datetime import datetime, timedelta

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Vendor
from app.services.alerts.generator import create_contract_expiring_alert


@celery_app.task(name="app.services.monitoring.contract_watcher.check_contract_expiry")
def check_contract_expiry():
    """
    Daily sweep for contracts expiring within 60 days.

    Per IMPLEMENTATION_PLAN.md §5, contract alerts fire at 60 days.
    """
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()

        alerts_created = 0
        now = datetime.utcnow()

        for vendor in vendors:
            if not vendor.contract_end:
                continue

            # Calculate days until contract expiry
            days_until_expiry = (vendor.contract_end - now).days

            # Alert if within 60 days
            if 0 < days_until_expiry <= 60:
                alert = create_contract_expiring_alert(
                    db,
                    vendor.id,
                    vendor.name,
                    days_until_expiry
                )
                if alert:
                    alerts_created += 1

        db.commit()
        return f"Contract expiry sweep complete: {alerts_created} alerts created"

    finally:
        db.close()
