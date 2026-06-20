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
    python backend/scripts/seed.py --skip-scoring   # load data only, no score compute
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
        "saas": "software_vendor",
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
    """
    Load vendor_registry.csv into the Vendor and related tables.

    Returns:
        (rows_processed, rows_succeeded, errors)
    """
    logger.info("Loading vendor registry from %s …", csv_path)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rows_processed = len(df)
    rows_succeeded = 0
    errors: list[dict] = []

    for row_num, row in df.iterrows():
        try:
            _upsert_vendor_row(row, db)
            rows_succeeded += 1
        except Exception as exc:
            error_detail = {"row": int(row_num) + 2, "reason": str(exc)}
            errors.append(error_detail)
            logger.warning("Row %d skipped — %s", int(row_num) + 2, exc)
            # DO NOT raise — partial failure tolerance

    logger.info(
        "Registry: %d processed, %d succeeded, %d failed.",
        rows_processed, rows_succeeded, len(errors),
    )
    return rows_processed, rows_succeeded, errors


def _upsert_vendor_row(row: pd.Series, db: Session) -> None:
    """
    Parse one CSV row and upsert Vendor + related entities.
    Raises on any parsing error so the caller can log and skip.
    """
    name = str(row.get("vendor_name", row.get("name", ""))).strip()
    if not name:
        raise ValueError("Missing vendor name")

    # ── Vendor core fields ───────────────────────────────────────────────────
    vendor_type = _normalize_vendor_type(row.get("vendor_type", "other"))
    contract_start = _parse_date(row.get("contract_start_date", row.get("contract_start")))
    contract_end   = _parse_date(row.get("contract_end_date", row.get("contract_end")))
    contract_status = str(row.get("contract_status", "active")).strip().lower()
    if contract_status not in ("active", "expired", "terminated", "pending"):
        contract_status = "active"

    annual_spend = None
    raw_spend = row.get("annual_spend", "")
    if raw_spend and raw_spend != "":
        try:
            annual_spend = float(str(raw_spend).replace(",", "").replace("$", ""))
        except ValueError:
            pass

    financial_signal = _normalize_financial_health(
        row.get("financial_health", row.get("financial_health_signal", "unknown"))
    )
    under_investigation = _parse_bool(row.get("under_investigation", False))
    last_assessed = _parse_date(row.get("last_assessed_at", row.get("last_assessed")))
    last_assessed_dt = datetime.combine(last_assessed, datetime.min.time()) if last_assessed else None

    # Upsert by name (treat name as the natural key for CSV imports)
    existing = db.query(Vendor).filter(Vendor.name == name).first()
    if existing:
        vendor = existing
    else:
        vendor = Vendor(id=str(uuid.uuid4()))
        db.add(vendor)

    vendor.name = name
    vendor.vendor_type = vendor_type
    vendor.contract_start = contract_start
    vendor.contract_end = contract_end
    vendor.contract_status = contract_status
    vendor.annual_spend = annual_spend
    vendor.financial_health_signal = financial_signal
    vendor.financial_health_source = "csv_import"
    vendor.under_investigation = under_investigation
    vendor.last_assessed_at = last_assessed_dt

    db.flush()  # ensure vendor.id is populated

    # ── Data access scope ────────────────────────────────────────────────────
    pii = _parse_bool(row.get("pii_access", row.get("has_pii_access", False)))
    financial_access = _parse_bool(row.get("financial_access", False))
    broad = _parse_bool(row.get("broad_system_access", False))
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

    # ── Certifications ───────────────────────────────────────────────────────
    cert_raw = str(row.get("certifications", row.get("certification", ""))).strip()
    expiry_raw = str(row.get("cert_expiry", row.get("certification_expiry", ""))).strip()
    cert_status_raw = str(row.get("cert_status", "unknown")).strip().lower()

    if cert_raw and cert_raw not in ("", "none", "nan"):
        cert_types = [c.strip() for c in cert_raw.split(",") if c.strip()]
        expiry_dates_raw = [e.strip() for e in expiry_raw.split(",")]

        for i, raw_cert in enumerate(cert_types):
            cert_type = _normalize_cert_type(raw_cert)
            expiry_date = _parse_date(expiry_dates_raw[i]) if i < len(expiry_dates_raw) else None

            # Determine status from expiry date if not explicitly set
            if cert_status_raw in ("current", "expired", "pending_renewal"):
                c_status = cert_status_raw
            elif expiry_date:
                c_status = "expired" if expiry_date < date.today() else "current"
            else:
                c_status = "unknown"

            # Upsert cert by vendor+type
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

    # ── Breach history ───────────────────────────────────────────────────────
    breached = _parse_bool(row.get("breached", row.get("has_breach", False)))
    breach_date = _parse_date(row.get("breach_date", row.get("last_breach_date")))
    breach_severity = str(row.get("breach_severity", "MEDIUM")).strip().upper()
    if breach_severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
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
                description=str(row.get("breach_description", "Imported from registry CSV")),
                resolved=_parse_bool(row.get("breach_resolved", False)),
            ))


# ─────────────────────────────────────────────────────────────────────────────
# Ground truth loader (evaluation-only)
# ─────────────────────────────────────────────────────────────────────────────

def load_ground_truth(csv_path: Path, db: Session) -> tuple[int, int, list[dict]]:
    """
    Load vendor_labels.csv into the ground_truth table.

    CRITICAL: This table is NEVER read by the scoring engine.
    It is read only by scripts/evaluate.py.
    """
    logger.info("Loading ground truth from %s …", csv_path)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rows_processed = len(df)
    rows_succeeded = 0
    errors: list[dict] = []

    # Clear existing ground truth before reload (idempotent)
    db.query(GroundTruth).delete()

    for row_num, row in df.iterrows():
        try:
            name = str(row.get("vendor_name", row.get("name", ""))).strip()
            if not name:
                raise ValueError("Missing vendor name")

            expired_certs_raw = str(row.get("expired_certifications", "")).strip()
            expired_certs = (
                [c.strip() for c in expired_certs_raw.split(",") if c.strip()]
                if expired_certs_raw and expired_certs_raw.lower() != "none"
                else []
            )

            db.add(GroundTruth(
                id=str(uuid.uuid4()),
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
            logger.warning("Ground truth row %d skipped — %s", int(row_num) + 2, exc)

    logger.info(
        "Ground truth: %d processed, %d succeeded, %d failed.",
        rows_processed, rows_succeeded, len(errors),
    )
    return rows_processed, rows_succeeded, errors


# ─────────────────────────────────────────────────────────────────────────────
# Scoring run after seed (optional)
# ─────────────────────────────────────────────────────────────────────────────

def run_initial_scoring(db: Session) -> None:
    """Score all vendors after seeding so the portfolio view has data immediately."""
    from app.services.scoring.engine import score_vendor_from_db
    from app.services.extraction.narrative import generate_rationale

    vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
    logger.info("Running initial scoring on %d vendors …", len(vendors))

    scored = 0
    for vendor in vendors:
        try:
            score_row = score_vendor_from_db(
                vendor_id=vendor.id,
                db=db,
                triggered_by="scheduled_sweep",
            )
            # Generate narrative after scoring
            narrative = generate_rationale(
                vendor_name=vendor.name,
                composite_score=score_row.composite_score,
                tier=score_row.tier,
                breach_subscore=score_row.breach_subscore,
                access_subscore=score_row.access_subscore,
                compliance_subscore=score_row.compliance_subscore,
                financial_subscore=score_row.financial_subscore,
                anomaly_types=score_row.anomaly_types or [],
            )
            score_row.rationale = narrative
            scored += 1
        except Exception as exc:
            logger.warning("Scoring failed for vendor %s (%s): %s", vendor.id, vendor.name, exc)

    logger.info("Scoring complete: %d/%d vendors scored.", scored, len(vendors))


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
        help="Load CSV data only, skip initial scoring run",
    )
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    registry_csv = data_dir / "vendor_registry.csv"
    labels_csv   = data_dir / "vendor_labels.csv"

    if not registry_csv.exists():
        logger.error("vendor_registry.csv not found at %s", registry_csv)
        sys.exit(1)

    # Ensure tables exist (create if running outside Docker Compose)
    logger.info("Ensuring DB tables exist …")
    Base.metadata.create_all(bind=engine)

    with get_db_context() as db:
        # 1 — Vendor registry
        reg_processed, reg_ok, reg_errors = load_vendor_registry(registry_csv, db)

        # 2 — Ground truth (if file exists)
        gt_processed = gt_ok = 0
        gt_errors: list[dict] = []
        if labels_csv.exists():
            gt_processed, gt_ok, gt_errors = load_ground_truth(labels_csv, db)
        else:
            logger.warning("vendor_labels.csv not found — skipping ground truth load")

        # 3 — Initial scoring
        if not args.skip_scoring:
            run_initial_scoring(db)

    # Summary
    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print(f"  Registry : {reg_ok}/{reg_processed} rows loaded  ({len(reg_errors)} errors)")
    if gt_processed:
        print(f"  Labels   : {gt_ok}/{gt_processed} rows loaded  ({len(gt_errors)} errors)")
    if reg_errors:
        print("\nRegistry errors:")
        for e in reg_errors[:20]:
            print(f"  Row {e['row']}: {e['reason']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
