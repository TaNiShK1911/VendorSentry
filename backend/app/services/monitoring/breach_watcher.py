"""Mock breach database polling (Celery task)"""
from datetime import datetime
import random

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Vendor, EvidenceSignal
from app.services.alerts.generator import create_new_breach_alert
from app.services.scoring.engine import score_vendor


@celery_app.task(name="app.services.monitoring.breach_watcher.poll_breach_db")
def poll_breach_db():
    """
    Poll mock breach database API for new breach signals.

    In production, this would call a real breach intelligence feed
    (HaveIBeenPwned Enterprise, etc.). For the hackathon, this is mocked
    but structured so a real adapter can be swapped in.

    Per IMPLEMENTATION_PLAN.md §5, new breach detection:
    - Creates EvidenceSignal record
    - Appends to vendor breach_history
    - Triggers immediate rescore
    - Fires NEW_BREACH alert
    """
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()

        breaches_detected = 0

        # Mock breach DB response (in production: call real API)
        # Randomly detect a breach for demo purposes (1% chance per vendor)
        for vendor in vendors:
            if random.random() < 0.01:  # 1% chance for demo
                # Mock breach data
                breach_data = {
                    "date": datetime.utcnow().isoformat(),
                    "severity": random.choice(["HIGH", "MEDIUM"]),
                    "source": "breach_db",
                    "description": f"Unauthorized access detected in {vendor.name} systems",
                    "resolved": False
                }

                # Create evidence signal
                signal = EvidenceSignal(
                    vendor_id=vendor.id,
                    source="breach_db",
                    signal_type="new_breach",
                    payload=breach_data,
                    received_at=datetime.utcnow()
                )
                db.add(signal)

                # Append to vendor breach history
                if not vendor.breach_history:
                    vendor.breach_history = []
                vendor.breach_history = vendor.breach_history + [breach_data]
                db.add(vendor)

                # Trigger rescore
                score = score_vendor(vendor, triggered_by="breach_detected")
                db.add(score)

                # Link signal to score
                db.flush()  # Get score ID
                signal.consumed_by_score_id = score.id

                # Create alert
                alert = create_new_breach_alert(
                    db,
                    vendor.id,
                    vendor.name,
                    breach_data["description"]
                )

                if alert:
                    breaches_detected += 1

        db.commit()
        return f"Breach DB poll complete: {breaches_detected} new breaches detected"

    finally:
        db.close()
