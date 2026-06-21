"""
Seed script — partial-failure-tolerant CSV ingestion.

Loads:
  1. vendor_registry.csv → vendors, certifications, breach_events,
                           data_access_scopes (live scoring tables)
  2. vendor_labels.csv   → ground_truth (EVALUATION ONLY — never feeds scoring)

ARCHITECTURAL RULES (AGENT.md + IMPLEMENTATION_PLAN.md §3.1):
- A malformed row logs an error and is SKIPPED; it never aborts the batch.
- vendor_labels.csv is loaded into ground_truth only — never into scoring tables.
- After loading, the scoring engine is run on all vendors to populate VendorScore.

Usage:
    python backend/scripts/seed.py [--data-dir path/to/sample_data]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

# Ensure backend/app is importable when running from repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.db.session import get_db_context
from app.models.vendor import Vendor
from app.models.vendor_score import VendorScore
from app.models.certification import Certification
from app.models.breach import BreachEvent
from app.models.data_access import DataAccessScope
from app.models.ground_truth import GroundTruth
from app.models.base import Base
from app.db.session import engine
from app.models.alert import Alert

from app.services.scoring.engine import score_vendor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_date(value) -> Optional[date]:
    """Try multiple common date formats; return None if unparseable."""
    if pd.isna(value) or value is None or str(value).strip() == "":
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None

def _parse_bool(value) -> bool:
    """Parse various boolean representations from CSV."""
    if pd.isna(value):
        return False
    v = str(value).strip().lower()
    return v in ("true", "1", "yes", "y")

def _normalize_vendor_type(raw: str) -> str:
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

def _normalize_financial_health(raw: str) -> str:
    mapping = {
        "stable": "stable", "good": "stable", "healthy": "stable",
        "watch": "watch", "concern": "watch", "moderate": "watch",
        "distressed": "distressed", "poor": "distressed", "critical": "distressed",
    }
    return mapping.get(str(raw).strip().lower(), "unknown")

def _normalize_cert_type(raw: str) -> str:
    mapping = {
        "soc2": "SOC2_TYPE2", "soc 2": "SOC2_TYPE2",
        "soc2_type1": "SOC2_TYPE1", "soc2_type2": "SOC2_TYPE2",
        "iso27001": "ISO_27001", "iso 27001": "ISO_27001",
        "pci": "PCI_DSS", "pci_dss": "PCI_DSS",
        "gdpr": "GDPR_COMPLIANCE",
        "hipaa": "HIPAA",
    }
    return mapping.get(str(raw).strip().lower(), "OTHER")

# ─────────────────────────────────────────────────────────────────────────────
# Registry loader
# ─────────────────────────────────────────────────────────────────────────────

def load_vendor_registry(csv_path: Path, db: Session) -> tuple[int, int, list[dict]]:
    logger.info("Loading vendor registry from %s …", csv_path)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rows_processed = len(df)
    rows_succeeded = 0
    errors: list[dict] = []

    # Sort the dataframe by last_audit_date to process chronologically
    df['last_audit_date_parsed'] = df.apply(lambda r: _parse_date(r.get("last_audit_date", r.get("last_assessed"))), axis=1)
    df = df.sort_values(by='last_audit_date_parsed', na_position='first')

    for name, group in df.groupby("vendor_name"):
        if not name or name == "nan":
            continue
            
        group = group.sort_values(by='last_audit_date_parsed', na_position='first')
        
        vendor = db.query(Vendor).filter(Vendor.name == name).first()
        if not vendor:
            vendor = Vendor(id=str(uuid.uuid4()), name=name)
            db.add(vendor)
            
        previous_score_id = None
        
        for idx, row in group.iterrows():
            try:
                _process_historical_row(row, db, vendor)
                db.flush()
                
                # Re-score vendor for this point in time
                breaches = vendor.breach_history
                certs = vendor.certifications
                scope = db.query(DataAccessScope).filter(DataAccessScope.vendor_id == vendor.id).first()
                result = score_vendor(vendor, breaches, certs, scope, triggered_by="scheduled_sweep")
                
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
                    rationale=f"Historical score update for {vendor.name}.",
                    computed_at=vendor.last_assessed_at or datetime.utcnow(),
                    previous_score_id=previous_score_id
                )
                db.add(score_row)
                db.flush()
                previous_score_id = score_row.id
                
                # Check for alerts if this is the final row for the vendor
                if row.equals(group.iloc[-1]):
                    _generate_alerts(vendor, result, db)
                
                rows_succeeded += 1
            except Exception as exc:
                error_detail = {"row": int(idx) + 2, "reason": str(exc)}
                errors.append(error_detail)
                logger.warning("Row %d skipped — %s", int(idx) + 2, exc)

    logger.info(
        "Registry: %d processed, %d succeeded, %d failed.",
        rows_processed, rows_succeeded, len(errors),
    )
    return rows_processed, rows_succeeded, errors

def _generate_alerts(vendor: Vendor, result, db: Session):
    for anomaly in result.anomaly_types:
        severity = "HIGH"
        if anomaly in ["BREACHED_VENDOR_HIGH_ACCESS", "VENDOR_UNDER_INVESTIGATION"]:
            severity = "CRITICAL"
        elif anomaly in ["RECENTLY_BREACHED_VENDOR"]:
            severity = "HIGH"
        
        # Simple deduplication key based on vendor and anomaly
        dedup_key = f"{vendor.id}:{anomaly}:{datetime.utcnow().strftime('%Y%m')}"
        
        # Check if active alert already exists
        existing_alert = db.query(Alert).filter(
            Alert.vendor_id == vendor.id,
            Alert.type == anomaly,
            Alert.resolved_at.is_(None)
        ).first()
        
        if not existing_alert:
            alert = Alert(
                id=str(uuid.uuid4()),
                vendor_id=vendor.id,
                type=anomaly,
                severity=severity,
                message=f"Vendor {vendor.name} flagged for {anomaly}",
                dedup_key=dedup_key
            )
            db.add(alert)

def _process_historical_row(row: pd.Series, db: Session, vendor: Vendor) -> None:
    vendor_type = _normalize_vendor_type(row.get("vendor_type", "other"))
    contract_end = _parse_date(row.get("contract_end_date", row.get("contract_end")))
    last_assessed = _parse_date(row.get("last_audit_date", row.get("last_assessed")))
    eval_date = last_assessed if last_assessed else date.today()
    
    if contract_end and contract_end < eval_date:
        contract_status = "expired"
    else:
        contract_status = "active"

    annual_spend = None
    raw_spend = row.get("annual_spend", "")
    if raw_spend and raw_spend != "":
        try:
            annual_spend = float(str(raw_spend).replace(",", "").replace("$", ""))
        except ValueError:
            pass

    financial_signal = _normalize_financial_health(
        row.get("financial_health", row.get("financial_health_signal", "stable"))
    )
    breach_status = str(row.get("breach_status", "")).strip()
    under_investigation = breach_status == "Under_Investigation"
    last_assessed_dt = datetime.combine(last_assessed, datetime.min.time()) if last_assessed else None

    vendor_id_val = str(row.get("vendor_id", "")).strip()
    vendor.source_vendor_id = vendor_id_val # update to the latest source_vendor_id
    
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

    cert_raw = str(row.get("compliance_certifications", row.get("certifications", ""))).strip()

    if cert_raw and cert_raw not in ("", "none", "nan"):
        cert_pairs = [c.strip() for c in cert_raw.split("|") if c.strip()]

        for pair in cert_pairs:
            parts = pair.split(":")
            raw_cert = parts[0].strip()
            cert_type = _normalize_cert_type(raw_cert)
            expiry_date = _parse_date(parts[1].strip()) if len(parts) > 1 else None

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

# ─────────────────────────────────────────────────────────────────────────────
# Ground truth loader
# ─────────────────────────────────────────────────────────────────────────────

def load_ground_truth(csv_path: Path, db: Session) -> tuple[int, int, list[dict]]:
    logger.info("Loading ground truth from %s …", csv_path)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rows_processed = len(df)
    rows_succeeded = 0
    errors: list[dict] = []

    db.query(GroundTruth).delete()

    for row_num, row in df.iterrows():
        try:
            name = str(row.get("vendor_name", row.get("name", ""))).strip()
            record_id = str(row.get("record_id", "")).strip()
            if not name:
                continue

            expired_certs_raw = str(row.get("expired_certifications", "")).strip()
            expired_certs = (
                [c.strip() for c in expired_certs_raw.split(",") if c.strip()]
                if expired_certs_raw and expired_certs_raw.lower() != "none"
                else []
            )

            db.add(GroundTruth(
                id=str(uuid.uuid4()),
                source_vendor_id=record_id if record_id else None,
                vendor_name=name,
                is_anomaly=_parse_bool(row.get("is_anomaly", False)),
                anomaly_type=str(row.get("anomaly_type", "")).strip() or None,
                severity=str(row.get("severity", "")).strip() or None,
                expired_certifications=expired_certs,
                explanation=str(row.get("explanation", "")).strip() or None,
            ))
            rows_succeeded += 1
        except Exception as exc:
            errors.append({"row": int(row_num) + 2, "reason": str(exc)})

    logger.info(
        "Ground truth: %d processed, %d succeeded, %d failed.",
        rows_processed, rows_succeeded, len(errors),
    )
    return rows_processed, rows_succeeded, errors

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VendorSentry seed script")
    parser.add_argument(
        "--data-dir",
        default=str(_REPO_ROOT / "backend" / "sample_data"),
        help="Directory containing vendor_registry.csv and vendor_labels.csv",
    )
    parser.add_argument(
        "--skip-scoring",
        action="store_true",
        help="Load CSV data only, skip initial scoring run (not used in historical mode)",
    )
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    registry_csv = data_dir / "vendor_registry.csv"
    labels_csv   = data_dir / "vendor_labels.csv"

    if not registry_csv.exists():
        logger.error("vendor_registry.csv not found at %s", registry_csv)
        sys.exit(1)

    logger.info("Ensuring DB tables exist …")
    Base.metadata.create_all(bind=engine)

    with get_db_context() as db:
        reg_processed, reg_ok, reg_errors = load_vendor_registry(registry_csv, db)

        gt_processed = gt_ok = 0
        gt_errors: list[dict] = []
        if labels_csv.exists():
            gt_processed, gt_ok, gt_errors = load_ground_truth(labels_csv, db)

    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print(f"  Registry : {reg_ok}/{reg_processed} rows loaded  ({len(reg_errors)} errors)")
    if gt_processed:
        print(f"  Labels   : {gt_ok}/{gt_processed} rows loaded  ({len(gt_errors)} errors)")
    print("=" * 60)

if __name__ == "__main__":
    main()
