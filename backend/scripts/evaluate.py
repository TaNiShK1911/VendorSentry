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
    """
    Score all vendors against ground truth and return full metrics dict.

    Returns a dict ready for JSON serialisation:
    {
      "run_at": ISO timestamp,
      "overall_accuracy": float,
      "vendor_count": int,
      "by_tier": {
        "CRITICAL": {"precision": …, "recall": …, "f1": …, "tp": …, "fp": …, "fn": …},
        …
      },
      "per_vendor": [ {vendor_name, predicted_tier, actual_tier, correct} ]
    }
    """
    logger.info("Loading ground truth …")
    gt_rows = db.query(GroundTruth).all()
    gt_by_name: dict[str, GroundTruth] = {gt.vendor_name.strip().lower(): gt for gt in gt_rows}

    if not gt_by_name:
        logger.warning("Ground truth table is empty — run seed.py first.")
        return {"error": "No ground truth data found. Run seed.py first."}

    logger.info("Loaded %d ground-truth records.", len(gt_by_name))

    vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
    logger.info("Scoring %d vendors …", len(vendors))

    # Counters per tier: {tier: {tp, fp, fn}}
    tier_counters: dict[str, dict[str, int]] = {
        t: {"tp": 0, "fp": 0, "fn": 0} for t in SEVERITY_ORDER
    }

    correct_total = 0
    per_vendor: list[dict] = []

    for vendor in vendors:
        # Run the live scoring engine (no DB write — pure compute only)
        result = score_vendor(
            vendor=vendor,
            breaches=vendor.breach_history or [],
            certs=vendor.certifications or [],
            scope=vendor.data_access_scope,
            triggered_by="evaluation",
        )

        predicted_severity = _highest_severity(result.anomaly_types)

        # Look up ground truth by vendor name
        gt = gt_by_name.get(vendor.name.strip().lower())
        if gt is None:
            # No ground truth for this vendor — skip from metrics
            per_vendor.append({
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "predicted_tier": predicted_severity,
                "actual_tier": "NO_GT",
                "correct": None,
            })
            continue

        actual_severity = _gt_severity(gt)
        correct = predicted_severity == actual_severity
        if correct:
            correct_total += 1

        per_vendor.append({
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "predicted_tier": predicted_severity,
            "actual_tier": actual_severity,
            "predicted_anomalies": result.anomaly_types,
            "actual_anomaly_type": gt.anomaly_type,
            "composite_score": result.composite_score,
            "correct": correct,
        })

        # Update per-tier TP/FP/FN
        for tier in SEVERITY_ORDER:
            predicted_positive = predicted_severity == tier
            actual_positive    = actual_severity == tier

            if predicted_positive and actual_positive:
                tier_counters[tier]["tp"] += 1
            elif predicted_positive and not actual_positive:
                tier_counters[tier]["fp"] += 1
            elif not predicted_positive and actual_positive:
                tier_counters[tier]["fn"] += 1

    # Vendors matched to GT
    matched_count = sum(1 for v in per_vendor if v["actual_tier"] != "NO_GT")
    overall_accuracy = correct_total / matched_count if matched_count else 0.0

    by_tier: dict[str, dict] = {}
    for tier in SEVERITY_ORDER:
        c = tier_counters[tier]
        p, r, f = _precision_recall_f1(c["tp"], c["fp"], c["fn"])
        by_tier[tier] = {
            "precision": p,
            "recall": r,
            "f1": f,
            "tp": c["tp"],
            "fp": c["fp"],
            "fn": c["fn"],
        }

    return {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "overall_accuracy": round(overall_accuracy, 4),
        "vendor_count": len(vendors),
        "matched_to_gt": matched_count,
        "by_tier": by_tier,
        "per_vendor": per_vendor,
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
        flag = "  ◄ PRIMARY" if tier in ("CRITICAL", "HIGH") else ""
        print(
            f"  {tier:<12} {m.get('precision', 0):>9.1%}  "
            f"{m.get('recall', 0):>9.1%}  {m.get('f1', 0):>7.1%}  "
            f"{m.get('tp', 0):>5}  {m.get('fp', 0):>5}  {m.get('fn', 0):>5}"
            f"{flag}"
        )

    print("=" * 65)
    print("\n  ◄ CRITICAL + HIGH recall are the primary eval focus (PRD §8)")

    by_tier = results.get("by_tier", {})
    critical_recall = by_tier.get("CRITICAL", {}).get("recall", 0)
    high_recall     = by_tier.get("HIGH", {}).get("recall", 0)

    if critical_recall >= 0.80:
        print(f"  ✓ CRITICAL recall {critical_recall:.1%} meets 80% target")
    else:
        print(f"  ✗ CRITICAL recall {critical_recall:.1%} BELOW 80% target — tune weights")

    if high_recall >= 0.80:
        print(f"  ✓ HIGH recall {high_recall:.1%} meets 80% target")
    else:
        print(f"  ✗ HIGH recall {high_recall:.1%} BELOW 80% target — tune weights")

    print()


# ─────────────────────────────────────────────────────────────────────────────
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
