"""
CSV Importer — shared parsing/normalization logic for vendor CSV ingestion.

Used by:
  - scripts/seed.py (initial database population)
  - POST /vendors/import (runtime CSV upload)

ARCHITECTURAL RULES:
  - A malformed row logs an error and is SKIPPED; it never aborts the batch.
  - vendor_labels.csv is never imported here — this module only handles
    vendor_registry.csv-shaped data.
  - After loading, the scoring engine is triggered for each vendor.
"""
from __future__ import annotations

import io
import logging
import uuid
from datetime import date, datetime
from typing import BinaryIO, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models.vendor import Vendor
from app.models.vendor_score import VendorScore
from app.models.certification import Certification
from app.models.breach import BreachEvent
from app.models.data_access import DataAccessScope
from app.models.alert import Alert
from app.services.scoring.engine import score_vendor, score_vendor_from_db

logger = logging.getLogger("csv_importer")


# ─────────────────────────────────────────────────────────────────────────────
# Public parsing helpers (shared by seed.py and API endpoint)
# ─────────────────────────────────────────────────────────────────────────────

def parse_date(value) -> Optional[date]:
    """Try multiple common date formats; return None if unparseable."""
    if pd.isna(value) or value is None or str(value).strip() == "":
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_bool(value) -> bool:
    """Parse various boolean representations from CSV."""
    if pd.isna(value):
        return False
    v = str(value).strip().lower()
    return v in ("true", "1", "yes", "y")


def normalize_vendor_type(raw: str) -> str:
    mapping = {
        "cloud": "cloud_provider",
        "cloud_provider": "cloud_provider",
        "contractor": "contractor",
        "mss": "mss_provider",
        "mss_provider": "mss_provider",
        "managed security": "mss_provider",
        "payment": "payment_processor",
        "payment_processor": "payment_processor",
        "software": "software_vendor",
        "software_vendor": "software_vendor",
        "saas": "saas_provider",
        "saas_provider": "saas_provider",
        "hardware_vendor": "hardware_vendor",
        "security_vendor": "security_vendor",
        "consulting": "consulting",
        "data_provider": "data_provider",
        "msp": "msp",
    }
    return mapping.get(str(raw).strip().lower(), "other")


def normalize_financial_health(raw: str) -> str:
    mapping = {
        "stable": "stable", "good": "stable", "healthy": "stable",
        "watch": "watch", "concern": "watch", "moderate": "watch",
        "distressed": "distressed", "poor": "distressed", "critical": "distressed",
    }
    return mapping.get(str(raw).strip().lower(), "unknown")


def normalize_cert_type(raw: str) -> str:
    mapping = {
        "soc2": "SOC2_TYPE2", "soc 2": "SOC2_TYPE2",
        "soc2_type1": "SOC2_TYPE1", "soc2_type2": "SOC2_TYPE2",
        "iso27001": "ISO_27001", "iso 27001": "ISO_27001",
        "pci": "PCI_DSS", "pci_dss": "PCI_DSS", "pci-dss": "PCI_DSS",
        "gdpr": "GDPR_COMPLIANCE",
        "hipaa": "HIPAA",
        "fedramp": "FEDRAMP",
    }
    return mapping.get(str(raw).strip().lower(), "OTHER")


# ─────────────────────────────────────────────────────────────────────────────
# Row processing (upserts vendor + related records)
# ─────────────────────────────────────────────────────────────────────────────

def process_vendor_row(row: pd.Series, db: Session) -> Vendor:
    """
    Upsert a single vendor row and its related records (certs, breaches, scope).
    Returns the Vendor ORM object.

    The row is expected to have columns matching vendor_registry.csv shape
    (after column normalization: lowercase, underscores).
    """
    record_id = str(row.get("vendor_id", "")).strip()
    name = str(row.get("vendor_name", "")).strip()

    if not record_id or record_id == "nan":
        raise ValueError("missing vendor_id")
    if not name or name == "nan":
        raise ValueError("missing vendor_name")

    # Deduplicate by vendor_id
    vendor = db.query(Vendor).filter(Vendor.source_vendor_id == record_id).first()
    if not vendor:
        vendor = Vendor(id=str(uuid.uuid4()), name=name, source_vendor_id=record_id)
        db.add(vendor)
        db.flush()

    # ── Update vendor fields ──────────────────────────────────────────────
    vendor_type = normalize_vendor_type(row.get("vendor_type", "other"))
    contract_end = parse_date(row.get("contract_end_date", row.get("contract_end")))
    last_assessed = parse_date(row.get("last_audit_date", row.get("last_assessed")))
    eval_date = date(2026, 4, 15)
    contract_status = "active"

    annual_spend = None
    raw_spend = row.get("annual_spend", "")
    if raw_spend and raw_spend != "":
        try:
            annual_spend = float(str(raw_spend).replace(",", "").replace("$", ""))
        except ValueError:
            pass

    financial_signal = normalize_financial_health(
        row.get("financial_health", row.get("financial_health_signal", "stable"))
    )
    breach_status = str(row.get("breach_status", "")).strip()
    under_investigation = breach_status == "Under_Investigation"
    last_assessed_dt = datetime.combine(last_assessed, datetime.min.time()) if last_assessed else None

    vendor.source_vendor_id = record_id
    vendor.vendor_type = vendor_type

    contact_name = str(row.get("contact_name", "")).strip()
    contact_email = str(row.get("contact_email", "")).strip()
    if contact_name or contact_email:
        vendor.contact = {
            "liaison_name": contact_name,
            "email": contact_email
        }

    vendor.contract_end = contract_end
    vendor.contract_status = contract_status
    vendor.annual_spend = annual_spend
    vendor.financial_health_signal = financial_signal
    vendor.financial_health_source = "csv_import"
    vendor.under_investigation = under_investigation
    vendor.last_assessed_at = last_assessed_dt

    try:
        raw_score = row.get("risk_score")
        if raw_score and str(raw_score).strip():
            vendor.source_risk_score = int(float(str(raw_score).strip()))
    except ValueError:
        pass

    db.flush()

    # ── Data access scope ─────────────────────────────────────────────────
    data_access_scope = str(row.get("data_access_scope", "")).strip()

    pii = False
    financial_access = False
    broad = False

    if data_access_scope == "Customer_PII":
        pii = True
    elif data_access_scope == "Financial_Data":
        financial_access = True
    elif data_access_scope == "All_Systems":
        broad = True
        pii = True
        financial_access = True

    systems_raw = str(row.get("systems", row.get("accessible_systems", ""))).strip()
    systems = [s.strip() for s in systems_raw.split(",") if s.strip()] if systems_raw else []

    scope = db.query(DataAccessScope).filter(DataAccessScope.vendor_id == vendor.id).first()
    if not scope:
        scope = DataAccessScope(id=str(uuid.uuid4()), vendor_id=vendor.id)
        db.add(scope)
    scope.pii_access = pii
    scope.financial_access = financial_access
    scope.broad_system_access = broad
    scope.systems = systems
    scope.scope_notes = data_access_scope

    # ── Certifications ────────────────────────────────────────────────────
    cert_raw = str(row.get("compliance_certifications", row.get("certifications", ""))).strip()

    if cert_raw and cert_raw not in ("", "none", "nan"):
        cert_pairs = [c.strip() for c in cert_raw.split("|") if c.strip()]

        for pair in cert_pairs:
            parts = pair.split(":")
            raw_cert = parts[0].strip()
            cert_type = normalize_cert_type(raw_cert)
            expiry_date = parse_date(parts[1].strip()) if len(parts) > 1 else None

            c_status = "expired" if (expiry_date and expiry_date < eval_date) else "current"

            existing_cert = (
                db.query(Certification)
                .filter(
                    Certification.vendor_id == vendor.id,
                    Certification.cert_type == cert_type,
                )
                .first()
            )
            if not existing_cert:
                existing_cert = Certification(
                    id=str(uuid.uuid4()),
                    vendor_id=vendor.id,
                    cert_type=cert_type,
                    source="csv_import",
                )
                db.add(existing_cert)
            existing_cert.status = c_status
            existing_cert.expiry_date = expiry_date

    # ── Breach events ─────────────────────────────────────────────────────
    breach_status = str(row.get("breach_status", "")).strip()
    breached = False
    breach_date = None
    breach_severity = "MEDIUM"

    if breach_status == "Recent_Breach_12mo":
        breached = True
        base_date = last_assessed or date.today()
        try:
            m = base_date.month - 6
            y = base_date.year
            if m <= 0:
                m += 12
                y -= 1
            breach_date = base_date.replace(year=y, month=m)
        except ValueError:
            breach_date = base_date
        breach_severity = "HIGH"
    elif breach_status == "Historical_Breach":
        breached = True
        base_date = last_assessed or date.today()
        try:
            breach_date = base_date.replace(year=base_date.year - 2)
        except ValueError:
            breach_date = base_date
        breach_severity = "MEDIUM"

    if breached and breach_date:
        existing_breach = (
            db.query(BreachEvent)
            .filter(
                BreachEvent.vendor_id == vendor.id,
                BreachEvent.breach_date == breach_date,
            )
            .first()
        )
        if not existing_breach:
            db.add(BreachEvent(
                id=str(uuid.uuid4()),
                vendor_id=vendor.id,
                breach_date=breach_date,
                severity=breach_severity,
                source="csv_import",
                description=f"Imported from registry CSV ({breach_status})",
                resolved=(breach_status == "Historical_Breach"),
            ))

    db.flush()
    return vendor


# Alert generation is now routed through app.services.alerts.generator.create_alert


def score_and_alert_vendor(vendor: Vendor, db: Session, triggered_by: str = "csv_import") -> VendorScore:
    """Score a vendor from DB data and generate alerts. Returns the new VendorScore."""
    last_score = (
        db.query(VendorScore)
        .filter(VendorScore.vendor_id == vendor.id)
        .order_by(VendorScore.computed_at.desc())
        .first()
    )
    previous_score_id = last_score.id if last_score else None

    breaches = vendor.breach_history
    certs = vendor.certifications
    scope = db.query(DataAccessScope).filter(DataAccessScope.vendor_id == vendor.id).first()
    result = score_vendor(vendor, breaches, certs, scope, triggered_by=triggered_by)

    score_row = VendorScore(
        id=str(uuid.uuid4()),
        vendor_id=vendor.id,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        composite_score=result.composite_score,
        tier=result.tier,
        status_color=result.status_color,
        anomaly_types=result.anomaly_types,
        triggered_by=result.triggered_by,
        rationale=f"Score update for {vendor.name} via {triggered_by}.",
        computed_at=datetime.utcnow(),
        previous_score_id=previous_score_id,
    )
    db.add(score_row)
    db.flush()

    from app.services.alerts.generator import create_alert
    from app.models.alert import AlertType, AlertSeverity

    for anomaly, severity in result.anomalies_with_severity:
        # We pass the current month as the trigger_value to allow month-based re-alerting
        # while using the standard SHA-256 deduplication mechanism.
        create_alert(
            db=db,
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            alert_type=AlertType(anomaly),
            severity=AlertSeverity(severity),
            message=f"Vendor {vendor.name} flagged for {anomaly}",
            trigger_value=datetime.utcnow().strftime('%Y%m')
        )
    return score_row


# ─────────────────────────────────────────────────────────────────────────────
# Batch import (used by both seed.py and POST /vendors/import)
# ─────────────────────────────────────────────────────────────────────────────

def import_csv_file(
    file_content: bytes | BinaryIO,
    db: Session,
    triggered_by: str = "csv_import",
) -> dict:
    """
    Parse a vendor_registry.csv-shaped file and upsert all rows.

    Returns:
        dict with keys: rows_processed, rows_succeeded, rows_failed, errors
    """
    if isinstance(file_content, bytes):
        file_content = io.BytesIO(file_content)

    df = pd.read_csv(file_content, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rows_processed = len(df)
    rows_succeeded = 0
    errors: list[dict] = []

    # Sort by last_audit_date to process chronologically
    df["_last_audit_parsed"] = df.apply(
        lambda r: parse_date(r.get("last_audit_date", r.get("last_assessed"))), axis=1
    )
    df = df.sort_values(by="_last_audit_parsed", na_position="first")

    for idx, row in df.iterrows():
        try:
            vendor = process_vendor_row(row, db)
            score_and_alert_vendor(vendor, db, triggered_by=triggered_by)
            rows_succeeded += 1
        except Exception as exc:
            error_detail = {"row": int(idx) + 2, "reason": str(exc)}
            errors.append(error_detail)
            logger.warning("Row %d skipped — %s", int(idx) + 2, exc)

    logger.info(
        "Import: %d processed, %d succeeded, %d failed.",
        rows_processed, rows_succeeded, len(errors),
    )

    return {
        "rows_processed": rows_processed,
        "rows_succeeded": rows_succeeded,
        "rows_failed": len(errors),
        "errors": errors,
    }
