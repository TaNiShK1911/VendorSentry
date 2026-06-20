"""Assessment overdue monitoring sweep (Celery task)"""
from datetime import datetime, timedelta

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Vendor
from app.services.alerts.generator import create_assessment_overdue_alert


@celery_app.task(name="app.services.monitoring.assessment_watcher.check_assessment_overdue")
def check_assessment_overdue():
    """
    Daily sweep for assessments overdue (>12 months since last review).

    Per IMPLEMENTATION_PLAN.md §5.
    """
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()

        alerts_created = 0
        now = datetime.utcnow()
        twelve_months_ago = now - timedelta(days=365)

        for vendor in vendors:
            if not vendor.last_assessed_at:
                # Never assessed - consider this overdue
                days_overdue = 365
            else:
                # Check if last assessment was more than 12 months ago
                if vendor.last_assessed_at < twelve_months_ago:
                    days_overdue = (now - vendor.last_assessed_at).days - 365
                else:
                    continue  # Not overdue yet

            # Create alert
            alert = create_assessment_overdue_alert(
                db,
                vendor.id,
                vendor.name,
                days_overdue
            )
            if alert:
                alerts_created += 1

        db.commit()
        return f"Assessment overdue sweep complete: {alerts_created} alerts created"

    finally:
        db.close()
