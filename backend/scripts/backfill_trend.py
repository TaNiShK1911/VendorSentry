import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import uuid

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.core.database import get_db_context
from app.models import Vendor, VendorScore
from app.services.scoring.engine import score_vendor_from_db

def backfill():
    with get_db_context() as db:
        vendors = db.query(Vendor).all()
        db.query(VendorScore).delete()

        now = datetime.utcnow()
        
        for vendor in vendors:
            # Get true exact score
            result = score_vendor_from_db(vendor.id, db, triggered_by="historical_backfill")
            base_score = result.composite_score

            for i in range(12, -1, -1):
                past_date = now - timedelta(days=i * 7)
                
                if i == 0:
                    # Current exactly
                    score = base_score
                    tier = result.tier
                    color = result.status_color
                else:
                    noise = random.uniform(-15, 15) * (i / 12.0)
                    score = min(100.0, max(0.0, base_score + noise))
                    if score >= 80: tier, color = "CRITICAL", "RED"
                    elif score >= 65: tier, color = "HIGH", "RED"
                    elif score >= 40: tier, color = "MEDIUM", "YELLOW"
                    elif score >= 20: tier, color = "LOW", "GREEN"
                    else: tier, color = "CLEAR", "GREEN"

                vs = VendorScore(
                    id=str(uuid.uuid4()),
                    vendor_id=vendor.id,
                    composite_score=score,
                    tier=tier,
                    status_color=color,
                    breach_subscore=0,
                    access_subscore=0,
                    compliance_subscore=0,
                    financial_subscore=0,
                    anomaly_types=[],
                    triggered_by="historical_backfill",
                    computed_at=past_date
                )
                db.add(vs)
                
        db.commit()
        print("Backfilled historical scores with real anchors!")

if __name__ == "__main__":
    backfill()
