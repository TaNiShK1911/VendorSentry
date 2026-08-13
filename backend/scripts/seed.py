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
from app.models.data_access import DataAccessScope
from app.models.ground_truth import GroundTruth
from app.models.base import Base
from app.db.session import engine

from app.services.scoring.engine import score_vendor

# Import shared helpers from the ingestion module
from app.services.ingestion.csv_importer import (
    parse_date as _parse_date,
    parse_bool as _parse_bool,
    normalize_vendor_type as _normalize_vendor_type,
    normalize_financial_health as _normalize_financial_health,
    normalize_cert_type as _normalize_cert_type,
    process_vendor_row,
    _generate_alerts,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed")


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

    for idx, row in df.iterrows():
        try:
            # Use the shared process_vendor_row from csv_importer
            vendor = process_vendor_row(row, db)

            # To properly link previous score, find the latest score for this vendor
            last_score = db.query(VendorScore).filter(VendorScore.vendor_id == vendor.id).order_by(VendorScore.computed_at.desc()).first()
            previous_score_id = last_score.id if last_score else None

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

            # Generate alerts for this vendor's current state
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
    db.commit()
    return rows_processed, rows_succeeded, errors


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
    db.commit()
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
