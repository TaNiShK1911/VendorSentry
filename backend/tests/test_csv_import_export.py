"""
Tests for CSV import/export endpoints.

Covers:
  - Round-trip: export → re-import → verify counts
  - Malformed rows: confirms bad rows are skipped, not fatal
"""
import csv
import io
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.vendor import Vendor
from app.models.vendor_score import VendorScore
from app.models.certification import Certification
from app.models.breach import BreachEvent
from app.models.data_access import DataAccessScope
from app.models.alert import Alert


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()


VALID_CSV = """\
vendor_id,vendor_name,vendor_type,contact_name,contact_email,compliance_certifications,data_access_scope,risk_score,breach_status,annual_spend,contract_end_date,last_audit_date
VND-T001,Test Vendor Alpha,Cloud_Provider,John Doe,john@alpha.com,SOC2:2027-06-15|ISO27001:2027-03-01,Customer_PII,45,No_Known_Breach,500000,2027-12-31,2026-06-01
VND-T002,Test Vendor Beta,Software_Vendor,Jane Doe,jane@beta.com,GDPR:2025-01-01,Financial_Data,88,Recent_Breach_12mo,200000,2026-03-15,2026-01-15
VND-T003,Test Vendor Gamma,MSP,Bob Smith,bob@gamma.com,,Internal_Data,30,No_Known_Breach,100000,2028-01-01,2026-07-01
"""

MALFORMED_CSV = """\
vendor_id,vendor_name,vendor_type,compliance_certifications,data_access_scope,risk_score,breach_status,annual_spend,contract_end_date,last_audit_date
VND-M001,Good Vendor,Cloud_Provider,SOC2:2027-06-15,Customer_PII,50,No_Known_Breach,300000,2027-12-31,2026-06-01
,Missing ID Vendor,Software_Vendor,,Internal_Data,40,No_Known_Breach,100000,2027-01-01,2026-03-01
VND-M003,,MSP,,Internal_Data,20,No_Known_Breach,50000,2028-01-01,2026-07-01
VND-M004,Another Good Vendor,Hardware_Vendor,ISO27001:2027-01-01,Financial_Data,60,No_Known_Breach,400000,2027-06-30,2026-05-01
"""


class TestCsvImport:
    """Test POST /vendors/import via the shared csv_importer module."""

    def test_import_valid_csv(self, db_session):
        """Import valid CSV — all rows should succeed."""
        from app.services.ingestion.csv_importer import import_csv_file

        result = import_csv_file(VALID_CSV.encode("utf-8"), db_session, triggered_by="test")

        assert result["rows_processed"] == 3
        assert result["rows_succeeded"] == 3
        assert result["rows_failed"] == 0
        assert result["errors"] == []

        # Verify vendors were created
        vendors = db_session.query(Vendor).all()
        assert len(vendors) == 3

        # Verify scores were created
        scores = db_session.query(VendorScore).all()
        assert len(scores) >= 3  # at least one score per vendor

        # Verify a high-risk vendor got the right score properties
        beta = db_session.query(Vendor).filter(Vendor.name == "Test Vendor Beta").first()
        assert beta is not None
        assert beta.source_risk_score == 88

    def test_import_malformed_rows_partial_success(self, db_session):
        """Import CSV with bad rows — bad rows skipped, good rows succeed."""
        from app.services.ingestion.csv_importer import import_csv_file

        result = import_csv_file(MALFORMED_CSV.encode("utf-8"), db_session, triggered_by="test")

        # Row 3 has missing vendor_id, Row 4 has missing vendor_name
        assert result["rows_processed"] == 4
        assert result["rows_succeeded"] >= 2  # VND-M001 and VND-M004 should succeed
        assert result["rows_failed"] >= 1     # At least the missing-ID row should fail
        assert len(result["errors"]) >= 1

        # Verify successful vendors exist
        good = db_session.query(Vendor).filter(Vendor.name == "Good Vendor").first()
        assert good is not None

    def test_import_upsert_deduplication(self, db_session):
        """Importing same vendor twice should upsert, not duplicate."""
        from app.services.ingestion.csv_importer import import_csv_file

        # Import once
        import_csv_file(VALID_CSV.encode("utf-8"), db_session, triggered_by="test")
        count1 = db_session.query(Vendor).count()

        # Import again
        import_csv_file(VALID_CSV.encode("utf-8"), db_session, triggered_by="test")
        count2 = db_session.query(Vendor).count()

        # Should not create duplicates
        assert count2 == count1

    def test_import_creates_certifications(self, db_session):
        """Import should create Certification records."""
        from app.services.ingestion.csv_importer import import_csv_file

        import_csv_file(VALID_CSV.encode("utf-8"), db_session, triggered_by="test")

        alpha = db_session.query(Vendor).filter(Vendor.name == "Test Vendor Alpha").first()
        certs = db_session.query(Certification).filter(
            Certification.vendor_id == alpha.id
        ).all()
        assert len(certs) == 2  # SOC2 and ISO27001

    def test_import_creates_breach_events(self, db_session):
        """Import should create BreachEvent for recently breached vendors."""
        from app.services.ingestion.csv_importer import import_csv_file

        import_csv_file(VALID_CSV.encode("utf-8"), db_session, triggered_by="test")

        beta = db_session.query(Vendor).filter(Vendor.name == "Test Vendor Beta").first()
        breaches = db_session.query(BreachEvent).filter(
            BreachEvent.vendor_id == beta.id
        ).all()
        assert len(breaches) >= 1

    def test_import_creates_data_access_scope(self, db_session):
        """Import should create DataAccessScope with correct flags."""
        from app.services.ingestion.csv_importer import import_csv_file

        import_csv_file(VALID_CSV.encode("utf-8"), db_session, triggered_by="test")

        alpha = db_session.query(Vendor).filter(Vendor.name == "Test Vendor Alpha").first()
        scope = db_session.query(DataAccessScope).filter(
            DataAccessScope.vendor_id == alpha.id
        ).first()
        assert scope is not None
        assert scope.pii_access is True  # Customer_PII
        assert scope.financial_access is False


class TestCsvExportRoundTrip:
    """Test export → re-import round trip."""

    def test_round_trip(self, db_session):
        """Export vendors to CSV, then re-import — data should survive the trip."""
        from app.services.ingestion.csv_importer import import_csv_file

        # Step 1: Import initial data
        result1 = import_csv_file(VALID_CSV.encode("utf-8"), db_session, triggered_by="test")
        assert result1["rows_succeeded"] == 3

        initial_count = db_session.query(Vendor).count()
        assert initial_count == 3

        # Step 2: Manually build an export CSV (simulating the export endpoint logic)
        from sqlalchemy import func

        vendors = db_session.query(Vendor).all()
        vendor_ids = [v.id for v in vendors]

        subq = db_session.query(
            VendorScore.vendor_id,
            func.max(VendorScore.computed_at).label("max_computed_at")
        ).filter(VendorScore.vendor_id.in_(vendor_ids)).group_by(VendorScore.vendor_id).subquery()

        latest_scores = db_session.query(VendorScore).join(
            subq,
            (VendorScore.vendor_id == subq.c.vendor_id) &
            (VendorScore.computed_at == subq.c.max_computed_at)
        ).all()
        score_map = {s.vendor_id: s for s in latest_scores}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "vendor_id", "vendor_name", "vendor_type",
            "composite_score", "tier", "status_color",
            "anomaly_types", "breach_status",
            "certifications", "contract_end_date", "last_audit_date",
            "data_access_scope", "risk_score",
        ])

        for vendor in vendors:
            score = score_map.get(vendor.id)
            writer.writerow([
                vendor.source_vendor_id or vendor.id,
                vendor.name,
                vendor.vendor_type,
                score.composite_score if score else "",
                score.tier if score else "",
                score.status_color if score else "",
                "",
                "No_Known_Breach",
                "",
                vendor.contract_end.isoformat() if vendor.contract_end else "",
                vendor.last_assessed_at.date().isoformat() if vendor.last_assessed_at else "",
                "Internal_Data",
                vendor.source_risk_score if vendor.source_risk_score else "",
            ])

        export_csv = output.getvalue().encode("utf-8")

        # Step 3: Re-import the exported CSV
        result2 = import_csv_file(export_csv, db_session, triggered_by="test_roundtrip")

        # Should succeed without errors (names deduplicate, so no new vendors)
        assert result2["rows_succeeded"] == 3
        assert result2["rows_failed"] == 0

        # Vendor count should stay the same (upsert, not duplicate)
        final_count = db_session.query(Vendor).count()
        assert final_count == initial_count
