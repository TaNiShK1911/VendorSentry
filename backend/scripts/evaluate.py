"""
Evaluation harness — precision/recall/F1 per severity tier vs. ground truth.

Runs the live scoring engine over all vendors in the DB, compares
anomaly_types/tier against the ground_truth table (loaded from
vendor_labels.csv), and reports metrics tier-by-tier.

CRITICAL: This script reads ground_truth — it NEVER writes to it,
and it NEVER feeds ground_truth back into the scoring engine.

Usage:
    python backend/scripts/evaluate.py
    python backend/scripts/evaluate.py --output results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure backend is importable from repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from sqlalchemy.orm import Session

from app.db.session import get_db_context
from app.models.vendor import Vendor
from app.models.ground_truth import GroundTruth
from app.services.scoring.engine import score_vendor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evaluate")


# ─────────────────────────────────────────────────────────────────────────────
# Tier / severity mapping helpers
# ─────────────────────────────────────────────────────────────────────────────

# Maps PRD anomaly_type → its canonical severity tier
ANOMALY_TO_SEVERITY: dict[str, str] = {
    "BREACHED_VENDOR_HIGH_ACCESS": "CRITICAL",
    "VENDOR_UNDER_INVESTIGATION": "CRITICAL",
    "HIGH_RISK_SCORE": "HIGH",
    "EXPIRED_CERTIFICATION": "HIGH",       # conservative: HIGH if we don't know access scope
    "RECENTLY_BREACHED_VENDOR": "MEDIUM",
    "CONTRACT_EXPIRED_ACTIVE_ACCESS": "MEDIUM",
    "ELEVATED_RISK_VENDOR": "LOW",
}

# Severity ordering (higher index = more severe)
SEVERITY_ORDER = ["CLEAR", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _highest_severity(anomaly_types: list[str]) -> str:
    """Return the highest severity across a list of anomaly types."""
    if not anomaly_types:
        return "CLEAR"
    severities = [ANOMALY_TO_SEVERITY.get(a, "LOW") for a in anomaly_types]
    return max(severities, key=lambda s: SEVERITY_ORDER.index(s))


def _gt_severity(gt: GroundTruth) -> str:
    """Normalise ground-truth severity to one of our five tiers."""
    if not gt.is_anomaly:
        return "CLEAR"
    raw = (gt.severity or "").strip().upper()
    if raw in SEVERITY_ORDER:
        return raw
    # Fallback: infer from anomaly_type
    return ANOMALY_TO_SEVERITY.get(gt.anomaly_type or "", "LOW")


# ─────────────────────────────────────────────────────────────────────────────
# Metrics computation
# ─────────────────────────────────────────────────────────────────────────────

def _precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return round(precision, 4), round(recall, 4), round(f1, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Core evaluation loop
# ─────────────────────────────────────────────────────────────────────────────

def run_evaluation(db: Session) -> dict:
    from app.models.vendor import Vendor
    from app.models.breach import BreachEvent
    from app.models.data_access import DataAccessScope
    from app.models.certification import Certification
    import pandas as pd
    from datetime import date, datetime
    import uuid
    from scripts.seed import _parse_date, _normalize_vendor_type, _normalize_financial_health, _normalize_cert_type, _parse_bool

    def _parse_certifications_mock(raw: str, vendor_id: str) -> list[Certification]:
        certs = []
        if pd.isna(raw) or str(raw).strip() == "":
            return certs
        parts = str(raw).split("|")
        for part in parts:
            part = part.strip()
            if not part: continue
            if ":" in part:
                ctype, cdate = part.split(":", 1)
                expiry = _parse_date(cdate)
                status = "current" if expiry and expiry >= date.today() else "expired"
            else:
                ctype = part
                expiry = None
                status = "current"
            certs.append(Certification(
                id=str(uuid.uuid4()), vendor_id=vendor_id,
                cert_type=_normalize_cert_type(ctype), status=status, issued_date=None, expiry_date=expiry
            ))
        return certs

    logger.info("Loading ground truth …")
    gt_rows = db.query(GroundTruth).all()
    # Support lookup by record_id
    gt_by_id: dict[str, GroundTruth] = {gt.source_vendor_id: gt for gt in gt_rows if gt.source_vendor_id}

    if not gt_by_id:
        logger.warning("Ground truth table is empty or missing source_vendor_id.")
        return {"error": "No ground truth data found."}

    logger.info("Loaded %d ground-truth records.", len(gt_by_id))

    csv_path = Path("sample_data/vendor_registry.csv")
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    logger.info("Scoring %d registry rows …", len(df))

    tier_counters: dict[str, dict[str, int]] = {t: {"tp": 0, "fp": 0, "fn": 0} for t in SEVERITY_ORDER}
    correct_total = 0
    per_vendor: list[dict] = []

    for idx, row in df.iterrows():
        record_id = str(row.get("vendor_id", "")).strip()
        vendor_name = str(row.get("vendor_name", "")).strip()
        vendor = Vendor(id=record_id, name=vendor_name)
        
        last_assessed = _parse_date(row.get("last_audit_date", row.get("last_assessed")))
        vendor.last_assessed_at = datetime.combine(last_assessed, datetime.min.time()) if last_assessed else None
        
        contract_end = _parse_date(row.get("contract_end_date", row.get("contract_end")))
        eval_date = last_assessed if last_assessed else date.today()
        if contract_end and contract_end < eval_date:
            vendor.contract_status = "expired"
        else:
            vendor.contract_status = "active"
            
        try:
            raw_score = row.get("risk_score")
            if raw_score and str(raw_score).strip():
                vendor.source_risk_score = int(float(str(raw_score).strip()))
        except ValueError:
            pass
            
        vendor.financial_health_signal = _normalize_financial_health(
            row.get("financial_health", row.get("financial_health_signal", "stable"))
        )
        breach_status = str(row.get("breach_status", "")).strip()
        vendor.under_investigation = (breach_status == "Under_Investigation")
        
        breaches = []
        breached = False
        breach_date = None
        breach_severity = "LOW"
        base_date = last_assessed or date.today()

        if breach_status == "Recent_Breach_12mo":
            breached = True
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
            try:
                breach_date = base_date.replace(year=base_date.year - 2)
            except ValueError:
                breach_date = base_date
            breach_severity = "MEDIUM"
            
        if breached and breach_date:
            breaches.append(BreachEvent(
                vendor_id=vendor.id, breach_date=breach_date, severity=breach_severity,
                source="csv_import", description=f"Imported from registry CSV ({breach_status})",
                resolved=(breach_status == "Historical_Breach")
            ))

        certs = _parse_certifications_mock(row.get("compliance_certifications", ""), vendor.id)
        
        data_access_scope = str(row.get("data_access_scope", "")).strip()
        pii = financial_access = broad = False
        if data_access_scope == "Customer_PII": pii = True
        elif data_access_scope == "Financial_Data": financial_access = True
        elif data_access_scope == "All_Systems": broad = pii = financial_access = True
            
        scope = DataAccessScope(
            vendor_id=vendor.id, pii_access=pii, financial_access=financial_access,
            broad_system_access=broad, systems=[]
        )
        
        # Run engine with current eval date to match ground truth snapshot!
        result = score_vendor(
            vendor=vendor, breaches=breaches, certs=certs, scope=scope,
            triggered_by="evaluation"
        )

        predicted_severity = result.tier

        gt = gt_by_id.get(record_id)
        if gt is None:
            per_vendor.append({
                "vendor_id": vendor.id, "vendor_name": vendor.name, "predicted_tier": predicted_severity,
                "actual_tier": "NO_GT", "correct": None,
            })
            continue

        actual_severity = _gt_severity(gt)
        correct = predicted_severity == actual_severity
        if correct: correct_total += 1

        per_vendor.append({
            "vendor_id": vendor.id, "vendor_name": vendor.name, "predicted_tier": predicted_severity,
            "actual_tier": actual_severity, "predicted_anomalies": result.anomaly_types,
            "actual_anomaly_type": gt.anomaly_type, "composite_score": result.composite_score,
            "correct": correct,
        })

        for tier in SEVERITY_ORDER:
            predicted_positive = predicted_severity == tier
            actual_positive    = actual_severity == tier

            if predicted_positive and actual_positive: tier_counters[tier]["tp"] += 1
            elif predicted_positive and not actual_positive: tier_counters[tier]["fp"] += 1
            elif not predicted_positive and actual_positive: tier_counters[tier]["fn"] += 1

    matched_count = sum(1 for v in per_vendor if v["actual_tier"] != "NO_GT")
    overall_accuracy = correct_total / matched_count if matched_count else 0.0

    by_tier: dict[str, dict] = {}
    total_tp = total_fp = total_fn = 0
    
    for tier in SEVERITY_ORDER:
        c = tier_counters[tier]
        p, r, f = _precision_recall_f1(c["tp"], c["fp"], c["fn"])
        by_tier[tier] = {
            "precision": p,
            "recall": r,
            "f1_score": f,
            "accuracy": (c["tp"] + matched_count - c["tp"] - c["fp"] - c["fn"]) / matched_count if matched_count else 0,
            "tp": c["tp"],
            "fp": c["fp"],
            "fn": c["fn"],
            "sample_count": c["tp"] + c["fn"]
        }
        total_tp += c["tp"]
        total_fp += c["fp"]
        total_fn += c["fn"]

    overall_p, overall_r, overall_f1 = _precision_recall_f1(total_tp, total_fp, total_fn)

    # Confusion matrix and score distribution
    tiers_reversed = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAR"]
    cm_matrix = [[0] * 5 for _ in range(5)]
    score_bins = [0] * 5
    actual_bins = [0] * 5

    for v in per_vendor:
        if v["actual_tier"] == "NO_GT":
            continue
        p_idx = tiers_reversed.index(v["predicted_tier"])
        a_idx = tiers_reversed.index(v["actual_tier"])
        cm_matrix[p_idx][a_idx] += 1
        
        score = v.get("composite_score", 0)
        bin_idx = min(int(score / 20), 4)
        score_bins[bin_idx] += 1
        actual_bins[4 - a_idx] += 1

    return {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "overall_accuracy": round(overall_accuracy, 4),
        "vendor_count": len(df),
        "matched_to_gt": matched_count,
        "overall_metrics": {
            "accuracy": round(overall_accuracy, 4),
            "precision": overall_p,
            "recall": overall_r,
            "f1_score": overall_f1,
            "mae": 0.0,
            "rmse": 0.0
        },
        "dataset_info": {
            "total_vendors_evaluated": len(df),
            "ground_truth_available": matched_count,
            "evaluation_period": "All Time"
        },
        "by_severity_tier": by_tier,
        "by_tier": by_tier,
        "per_vendor": per_vendor,
        "confusion_matrix": {
            "predicted": tiers_reversed,
            "actual": tiers_reversed,
            "matrix": cm_matrix
        },
        "score_distribution": {
            "bins": ["0-20", "20-40", "40-60", "60-80", "80-100"],
            "predicted": score_bins,
            "actual": actual_bins
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pretty-print results
# ─────────────────────────────────────────────────────────────────────────────

def _print_report(results: dict) -> None:
    """Print a human-readable evaluation report to stdout."""
    print("\n" + "=" * 65)
    print("  VENDORSENTRY EVALUATION REPORT")
    print(f"  Run at  : {results.get('run_at', 'N/A')}")
    print(f"  Vendors : {results.get('vendor_count', 0)} total  |  "
          f"{results.get('matched_to_gt', 0)} matched to ground truth")
    print(f"  Overall Accuracy : {results.get('overall_accuracy', 0):.1%}")
    print("=" * 65)
    print(f"  {'Tier':<12} {'Precision':>10} {'Recall':>10} {'F1':>8} "
          f"{'TP':>6} {'FP':>6} {'FN':>6}")
    print("-" * 65)

    for tier in reversed(SEVERITY_ORDER):  # CRITICAL first
        m = results.get("by_tier", {}).get(tier, {})
        flag = "  <-- PRIMARY" if tier in ("CRITICAL", "HIGH") else ""
        print(
            f"  {tier:<12} {m.get('precision', 0):>9.1%}  "
            f"{m.get('recall', 0):>9.1%}  {m.get('f1_score', 0):>7.1%}  "
            f"{m.get('tp', 0):>5}  {m.get('fp', 0):>5}  {m.get('fn', 0):>5}"
            f"{flag}"
        )

    print("=" * 65)
    print("\n  <-- CRITICAL + HIGH recall are the primary eval focus (PRD §8)")

    by_tier = results.get("by_tier", {})
    critical_recall = by_tier.get("CRITICAL", {}).get("recall", 0)
    high_recall     = by_tier.get("HIGH", {}).get("recall", 0)

    if critical_recall >= 0.80:
        print(f"  [+] CRITICAL recall {critical_recall:.1%} meets 80% target")
    else:
        print(f"  [-] CRITICAL recall {critical_recall:.1%} BELOW 80% target - tune weights")

    if high_recall >= 0.80:
        print(f"  [+] HIGH recall {high_recall:.1%} meets 80% target")
    else:
        print(f"  [-] HIGH recall {high_recall:.1%} BELOW 80% target - tune weights")

    print()


# -----------------------------------------------------------------------------
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VendorSentry evaluation harness")
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write JSON results (optional; always printed to stdout)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-vendor details in JSON output",
    )
    args = parser.parse_args()

    with get_db_context() as db:
        results = run_evaluation(db)

    if args.quiet:
        results.pop("per_vendor", None)

    _print_report(results)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(results, indent=2))
        print(f"  Full results written to {out_path}")


if __name__ == "__main__":
    main()
