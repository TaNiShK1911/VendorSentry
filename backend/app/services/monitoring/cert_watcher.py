"""Certification expiry monitoring sweep (Celery task)"""
from datetime import datetime, timedelta

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Vendor
from app.services.alerts.generator import create_cert_expiring_alert


@celery_app.task(name="app.services.monitoring.cert_watcher.check_cert_expiry")
def check_cert_expiry():
    """
    Daily sweep for certifications expiring within 60/30/7 days.

    Generates escalating alerts per IMPLEMENTATION_PLAN.md §5.
    Idempotent - uses dedup logic to prevent spam.
    """
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()

        alerts_created = 0
        now = datetime.utcnow().date()

        for vendor in vendors:
            if not vendor.certifications:
                continue

            for cert in vendor.certifications:
                expiry_date = cert.expiry_date
                if not expiry_date:
                    continue

                # Calculate days until expiry
                days_until_expiry = (expiry_date - now).days

                # Check if we should alert (60, 30, or 7 days)
                if days_until_expiry in [60, 30, 7] or (0 < days_until_expiry < 7):
                    alert = create_cert_expiring_alert(
                        db,
                        vendor.id,
                        vendor.name,
                        cert.cert_type,
                        days_until_expiry
                    )
                    if alert:
                        alerts_created += 1

        db.commit()
        return f"Cert expiry sweep complete: {alerts_created} alerts created"

    finally:
        db.close()
