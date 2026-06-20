"""
Generate realistic sample_data/vendor_registry.csv and vendor_labels.csv
matching the shapes the seed script expects.

Run from the repo root:
    python backend/scripts/generate_sample_data.py
"""
from __future__ import annotations

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

_REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = _REPO_ROOT / "backend" / "sample_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Lookup tables ────────────────────────────────────────────────────────────
VENDOR_NAMES = [
    "Acme Cloud Storage", "BlueShield Analytics", "ClearPath Networks",
    "DataVault Systems", "EdgeSecure Ltd", "FortKnox Payments",
    "GlobalMesh MSS", "HealthBridge IT", "IntelliGuard Software",
    "JetStream Infrastructure", "KeyLock Security", "LibertyData Corp",
    "MegaScale Hosting", "NetSafe Solutions", "OmniCloud Services",
    "PrecisionPay Ltd", "QuantumRisk Analytics", "RapidDeploy Systems",
    "SecureHarbor Inc", "TrustFrame Technologies", "UltraSecure MSS",
    "VaultMaster Corp", "WebArmor Ltd", "XcelData Solutions",
    "YieldSecure Analytics", "ZenCloud Systems",
]

TYPES = ["cloud_provider","contractor","mss_provider","payment_processor","software_vendor"]
CERT_TYPES = ["SOC2_TYPE2","ISO_27001","PCI_DSS","HIPAA","SOC2_TYPE1"]
FIN_HEALTH = ["stable","watch","distressed","unknown"]
SYSTEMS = ["customer_db","object_storage","billing_system","crm","erp","data_warehouse"]

def rand_date(start_offset_days: int, end_offset_days: int) -> date:
    offset = random.randint(start_offset_days, end_offset_days)
    return date.today() + timedelta(days=offset)

def rand_vendor_name(i: int) -> str:
    base = VENDOR_NAMES[i % len(VENDOR_NAMES)]
    suffix = f" {i // len(VENDOR_NAMES) + 1}" if i >= len(VENDOR_NAMES) else ""
    return base + suffix

# ── Build 400 vendors ────────────────────────────────────────────────────────
registry_rows = []
label_rows    = []

for i in range(400):
    name = rand_vendor_name(i)
    vtype = random.choice(TYPES)
    spend = round(random.uniform(10_000, 5_000_000), 2)
    fin   = random.choices(FIN_HEALTH, weights=[55, 25, 10, 10])[0]

    contract_start = rand_date(-730, -365)
    contract_end   = rand_date(-90, 730)   # some already expired
    c_status = "expired" if contract_end < date.today() else "active"

    # Certs
    num_certs = random.randint(0, 3)
    cert_list = random.sample(CERT_TYPES, min(num_certs, len(CERT_TYPES)))
    cert_expiries = []
    cert_statuses = []
    for _ in cert_list:
        exp = rand_date(-180, 540)   # some expired
        cert_expiries.append(str(exp))
        cert_statuses.append("expired" if exp < date.today() else "current")

    has_expired_cert = any(s == "expired" for s in cert_statuses)

    # Access
    pii       = random.choices([True, False], weights=[40, 60])[0]
    financial = random.choices([True, False], weights=[30, 70])[0]
    broad     = random.choices([True, False], weights=[25, 75])[0]
    sys_list  = random.sample(SYSTEMS, random.randint(0, 3))

    # Breach
    breached = random.choices([True, False], weights=[20, 80])[0]
    breach_date_val = str(rand_date(-400, -1)) if breached else ""
    breach_sev = random.choice(["HIGH","MEDIUM","CRITICAL","LOW"]) if breached else ""

    # Investigation
    under_inv = random.choices([True, False], weights=[3, 97])[0]

    # Last assessed
    last_assessed = rand_date(-500, -1)

    registry_rows.append({
        "vendor_name": name,
        "vendor_type": vtype,
        "annual_spend": spend,
        "contract_start": str(contract_start),
        "contract_end": str(contract_end),
        "contract_status": c_status,
        "financial_health": fin,
        "pii_access": str(pii).lower(),
        "financial_access": str(financial).lower(),
        "broad_system_access": str(broad).lower(),
        "systems": ",".join(sys_list),
        "certifications": ",".join(cert_list),
        "cert_expiry": ",".join(cert_expiries),
        "cert_status": cert_statuses[0] if cert_statuses else "",
        "breached": str(breached).lower(),
        "breach_date": breach_date_val,
        "breach_severity": breach_sev,
        "breach_resolved": str(random.choice([True, False])).lower() if breached else "",
        "under_investigation": str(under_inv).lower(),
        "last_assessed": str(last_assessed),
    })

    # ── Ground truth labelling ───────────────────────────────────────────────
    is_anomaly = False
    anomaly_type = ""
    severity = ""
    explanation = ""

    recent_breach = breached and breach_date_val and (
        date.today() - date.fromisoformat(breach_date_val)
    ).days <= 365

    if under_inv:
        is_anomaly = True
        anomaly_type = "VENDOR_UNDER_INVESTIGATION"
        severity = "CRITICAL"
        explanation = f"{name} is currently under regulatory investigation."
    elif recent_breach and (pii or financial):
        is_anomaly = True
        anomaly_type = "BREACHED_VENDOR_HIGH_ACCESS"
        severity = "CRITICAL"
        explanation = f"{name} had a breach within 12 months and has sensitive data access."
    elif has_expired_cert and (pii or financial):
        is_anomaly = True
        anomaly_type = "EXPIRED_CERTIFICATION"
        severity = "HIGH"
        explanation = f"{name} has expired certification(s) and accesses sensitive data."
    elif recent_breach:
        is_anomaly = True
        anomaly_type = "RECENTLY_BREACHED_VENDOR"
        severity = "MEDIUM"
        explanation = f"{name} had a security breach within the last 12 months."
    elif c_status == "expired" and c_status == "active":
        is_anomaly = True
        anomaly_type = "CONTRACT_EXPIRED_ACTIVE_ACCESS"
        severity = "MEDIUM"
        explanation = f"{name} contract expired but vendor still has system access."
    elif has_expired_cert:
        is_anomaly = True
        anomaly_type = "EXPIRED_CERTIFICATION"
        severity = "MEDIUM"
        explanation = f"{name} has expired certification(s)."

    label_rows.append({
        "vendor_name": name,
        "is_anomaly": str(is_anomaly).lower(),
        "anomaly_type": anomaly_type,
        "severity": severity,
        "expired_certifications": ",".join(
            c for c, s in zip(cert_list, cert_statuses) if s == "expired"
        ),
        "explanation": explanation,
    })

# ── Write CSVs ────────────────────────────────────────────────────────────────
reg_path = OUT_DIR / "vendor_registry.csv"
with open(reg_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=registry_rows[0].keys())
    writer.writeheader()
    writer.writerows(registry_rows)
print(f"Written {len(registry_rows)} rows → {reg_path}")

lbl_path = OUT_DIR / "vendor_labels.csv"
with open(lbl_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=label_rows[0].keys())
    writer.writeheader()
    writer.writerows(label_rows)
print(f"Written {len(label_rows)} rows → {lbl_path}")

anomaly_count = sum(1 for r in label_rows if r["is_anomaly"] == "true")
print(f"\nLabel stats: {anomaly_count} anomalies / {len(label_rows)} total "
      f"({anomaly_count/len(label_rows):.0%} anomaly rate)")
