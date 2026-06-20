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

from app.models.base import Base
from app.core.database import engine, SessionLocal
from app.models.vendor import Vendor
from app.models.vendor_score import VendorScore
from app.models.certification import Certification
from app.models.breach import BreachEvent
from app.models.data_access import DataAccessScope
from app.models.alert import Alert
from app.models.evidence_signal import EvidenceSignal
from app.models.audit_log import AuditLogEntry
from app.models.ground_truth import GroundTruth
from app.models.extraction_job import ExtractionJob


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


def seed_data():
    """Seed sample vendors, scores, alerts for demo."""
    db = SessionLocal()

    # Check if data already exists
    existing = db.query(Vendor).count()
    if existing > 0:
        print(f"Database already has {existing} vendors. Skipping seed.")
        db.close()
        return

    print("Seeding sample data...")

    # Sample vendors
    vendors_data = [
        {
            "name": "CloudVault Solutions",
            "vendor_type": "cloud_provider",
            "contact": {"liaison_name": "John Smith", "email": "john@cloudvault.io"},
            "annual_spend": 450000.00,
            "contract_start": date(2024, 1, 1),
            "contract_end": date(2026, 12, 31),
            "contract_status": "active",
            "financial_health_signal": "stable",
            "financial_health_source": "public_records_enrichment",
        },
        {
            "name": "DataStream Analytics",
            "vendor_type": "software_vendor",
            "contact": {"liaison_name": "Sarah Lee", "email": "sarah@datastream.io"},
            "annual_spend": 280000.00,
            "contract_start": date(2023, 6, 1),
            "contract_end": date(2025, 5, 31),
            "contract_status": "active",
            "financial_health_signal": "watch",
            "financial_health_source": "public_records_enrichment",
        },
        {
            "name": "SecureNet MSS",
            "vendor_type": "mss_provider",
            "contact": {"liaison_name": "Mike Johnson", "email": "mike@securenet.com"},
            "annual_spend": 620000.00,
            "contract_start": date(2024, 3, 1),
            "contract_end": date(2027, 2, 28),
            "contract_status": "active",
            "financial_health_signal": "stable",
            "financial_health_source": "public_records_enrichment",
        },
        {
            "name": "PayFlow Processors",
            "vendor_type": "payment_processor",
            "contact": {"liaison_name": "Lisa Chen", "email": "lisa@payflow.com"},
            "annual_spend": 180000.00,
            "contract_start": date(2023, 1, 1),
            "contract_end": date(2025, 12, 31),
            "contract_status": "active",
            "financial_health_signal": "distressed",
            "financial_health_source": "public_records_enrichment",
            "under_investigation": True,
        },
        {
            "name": "TechBridge Consulting",
            "vendor_type": "contractor",
            "contact": {"liaison_name": "David Park", "email": "david@techbridge.co"},
            "annual_spend": 95000.00,
            "contract_start": date(2024, 7, 1),
            "contract_end": date(2025, 6, 30),
            "contract_status": "active",
            "financial_health_signal": "stable",
            "financial_health_source": "manual",
        },
        {
            "name": "InfraCore Systems",
            "vendor_type": "cloud_provider",
            "contact": {"liaison_name": "Emma Wilson", "email": "emma@infracore.io"},
            "annual_spend": 820000.00,
            "contract_start": date(2023, 4, 1),
            "contract_end": date(2026, 3, 31),
            "contract_status": "active",
            "financial_health_signal": "stable",
            "financial_health_source": "public_records_enrichment",
        },
        {
            "name": "CyberShield Defense",
            "vendor_type": "mss_provider",
            "contact": {"liaison_name": "Robert Kim", "email": "robert@cybershield.com"},
            "annual_spend": 340000.00,
            "contract_start": date(2024, 1, 15),
            "contract_end": date(2025, 1, 14),
            "contract_status": "active",
            "financial_health_signal": "watch",
            "financial_health_source": "public_records_enrichment",
        },
        {
            "name": "DataGuard Pro",
            "vendor_type": "software_vendor",
            "contact": {"liaison_name": "Jennifer Brown", "email": "jen@dataguard.io"},
            "annual_spend": 150000.00,
            "contract_start": date(2022, 11, 1),
            "contract_end": date(2025, 10, 31),
            "contract_status": "active",
            "financial_health_signal": "stable",
            "financial_health_source": "manual",
        },
        {
            "name": "QuantumPay",
            "vendor_type": "payment_processor",
            "contact": {"liaison_name": "Alex Turner", "email": "alex@quantumpay.com"},
            "annual_spend": 520000.00,
            "contract_start": date(2024, 6, 1),
            "contract_end": date(2027, 5, 31),
            "contract_status": "active",
            "financial_health_signal": "stable",
            "financial_health_source": "public_records_enrichment",
        },
        {
            "name": "NexGen IT Services",
            "vendor_type": "contractor",
            "contact": {"liaison_name": "Maria Garcia", "email": "maria@nexgen.com"},
            "annual_spend": 210000.00,
            "contract_start": date(2023, 9, 1),
            "contract_end": date(2025, 8, 31),
            "contract_status": "active",
            "financial_health_signal": "unknown",
            "financial_health_source": "unknown",
        },
    ]

    created_vendors = []
    for vd in vendors_data:
        vendor = Vendor(**vd)
        vendor.last_assessed_at = datetime.utcnow() - timedelta(days=int(hash(vd["name"]) % 180))
        db.add(vendor)
        db.flush()
        created_vendors.append(vendor)

    # Add data access scopes
    scopes = [
        (0, True, True, True, ["AWS S3", "Kubernetes", "CloudWatch"]),
        (1, True, False, False, ["Analytics Dashboard"]),
        (2, False, False, True, ["SIEM", "Firewall Mgmt", "IDS/IPS"]),
        (3, True, True, False, ["Payment Gateway", "Transaction DB"]),
        (4, False, False, False, ["JIRA", "Confluence"]),
        (5, True, True, True, ["EC2", "RDS", "Lambda", "S3"]),
        (6, False, False, True, ["SOC Platform", "Endpoint Protection"]),
        (7, True, False, False, ["Backup System", "DLP"]),
        (8, True, True, False, ["Payment API", "Ledger System"]),
        (9, False, False, False, ["ServiceNow", "Ticketing"]),
    ]

    for idx, pii, fin, broad, systems in scopes:
        scope = DataAccessScope(
            vendor_id=created_vendors[idx].id,
            pii_access=pii,
            financial_access=fin,
            broad_system_access=broad,
            systems=systems,
        )
        db.add(scope)

    # Add certifications
    cert_data = [
        (0, "SOC2_TYPE2", "current", date(2024, 1, 1), date(2025, 12, 31)),
        (0, "ISO_27001", "current", date(2023, 6, 1), date(2026, 5, 31)),
        (1, "SOC2_TYPE1", "expired", date(2022, 1, 1), date(2024, 12, 31)),
        (2, "PCI_DSS", "current", date(2024, 3, 1), date(2025, 2, 28)),
        (2, "ISO_27001", "current", date(2024, 1, 1), date(2027, 12, 31)),
        (3, "PCI_DSS", "expired", date(2022, 6, 1), date(2024, 5, 31)),
        (5, "SOC2_TYPE2", "current", date(2024, 4, 1), date(2026, 3, 31)),
        (5, "ISO_27001", "current", date(2024, 1, 1), date(2027, 12, 31)),
        (5, "PCI_DSS", "current", date(2024, 6, 1), date(2025, 5, 31)),
        (6, "SOC2_TYPE1", "current", date(2024, 1, 1), date(2025, 12, 31)),
        (8, "PCI_DSS", "current", date(2024, 7, 1), date(2025, 6, 30)),
    ]

    for idx, ctype, cstatus, issued, expiry in cert_data:
        cert = Certification(
            vendor_id=created_vendors[idx].id,
            cert_type=ctype,
            status=cstatus,
            issued_date=issued,
            expiry_date=expiry,
            source="manual",
        )
        db.add(cert)

    # Add breach events
    breach_data = [
        (1, date(2024, 8, 15), "HIGH", "Data exposure via misconfigured API endpoint"),
        (3, date(2024, 11, 1), "CRITICAL", "Payment card data breach affecting 50K records"),
        (3, date(2023, 5, 20), "MEDIUM", "Phishing incident — employee credentials compromised"),
        (6, date(2024, 6, 10), "LOW", "Minor unauthorized access attempt — blocked"),
    ]

    for idx, bdate, severity, desc in breach_data:
        breach = BreachEvent(
            vendor_id=created_vendors[idx].id,
            breach_date=bdate,
            severity=severity,
            source="breach_db",
            description=desc,
            resolved=(severity != "CRITICAL"),
        )
        db.add(breach)

    db.flush()

    # Compute scores for each vendor
    from app.services.scoring.engine import score_vendor as compute_score

    score_configs = [
        # (idx, composite_score, tier, status_color)
        (0, 22.0, "LOW", "GREEN"),
        (1, 58.0, "MEDIUM", "YELLOW"),
        (2, 15.0, "LOW", "GREEN"),
        (3, 82.0, "CRITICAL", "RED"),
        (4, 20.0, "LOW", "GREEN"),
        (5, 12.0, "CLEAR", "GREEN"),
        (6, 35.0, "MEDIUM", "YELLOW"),
        (7, 28.0, "LOW", "GREEN"),
        (8, 18.0, "LOW", "GREEN"),
        (9, 40.0, "MEDIUM", "YELLOW"),
    ]

    for idx, composite, tier, color in score_configs:
        vendor = created_vendors[idx]
        # Try real scoring first
        try:
            result = compute_score(
                vendor,
                vendor.breach_history,
                vendor.certifications,
                vendor.data_access_scope,
                triggered_by="manual"
            )
            score = VendorScore(
                vendor_id=vendor.id,
                breach_subscore=result.breach_subscore,
                access_subscore=result.access_subscore,
                compliance_subscore=result.compliance_subscore,
                financial_subscore=result.financial_subscore,
                composite_score=result.composite_score,
                tier=result.tier,
                status_color=result.status_color,
                anomaly_types=result.anomaly_types,
                triggered_by="manual",
                rationale=f"Initial scoring for {vendor.name}.",
            )
        except Exception:
            # Fallback to pre-configured values
            score = VendorScore(
                vendor_id=vendor.id,
                breach_subscore=composite * 0.4,
                access_subscore=composite * 0.25,
                compliance_subscore=composite * 0.2,
                financial_subscore=composite * 0.15,
                composite_score=composite,
                tier=tier,
                status_color=color,
                anomaly_types=[],
                triggered_by="manual",
                rationale=f"Initial scoring for {vendor.name}.",
            )
        db.add(score)

    # Add alerts
    alert_data = [
        (1, "CERT_EXPIRING", "HIGH", "SOC 2 Type I certification for DataStream Analytics expired on 2024-12-31"),
        (3, "NEW_BREACH", "CRITICAL", "Critical payment card data breach detected for PayFlow Processors affecting 50K records"),
        (3, "CERT_EXPIRING", "HIGH", "PCI-DSS certification for PayFlow Processors expired on 2024-05-31"),
        (3, "SCORE_TIER_CHANGED", "CRITICAL", "PayFlow Processors risk tier escalated from HIGH to CRITICAL"),
        (6, "CONTRACT_EXPIRING", "MEDIUM", "CyberShield Defense contract expires in 30 days (2025-01-14)"),
        (9, "ASSESSMENT_OVERDUE", "MEDIUM", "NexGen IT Services has not been assessed in over 12 months"),
    ]

    for idx, atype, severity, message in alert_data:
        alert = Alert(
            vendor_id=created_vendors[idx].id,
            type=atype,
            severity=severity,
            message=message,
            dedup_key=f"{created_vendors[idx].id}:{atype}:{str(uuid.uuid4())[:8]}",
        )
        db.add(alert)

    db.commit()
    print(f"Seeded {len(created_vendors)} vendors with scores, certs, breaches, and alerts.")
    db.close()


if __name__ == "__main__":
    create_tables()
    seed_data()
    print("Database initialization complete!")
