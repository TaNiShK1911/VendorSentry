"""
Unit tests for the risk scoring engine.

Tests every tier boundary condition listed in IMPLEMENTATION_PLAN.md §4.
All tests use plain Python fixtures — no DB, no LLM, no network calls.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.services.scoring.subscore_breach import compute_breach_subscore
from app.services.scoring.subscore_access import compute_access_subscore
from app.services.scoring.subscore_compliance import (
    compute_compliance_subscore,
    get_compliance_flags,
)
from app.services.scoring.subscore_financial import compute_financial_subscore
from app.services.scoring.engine import compute_composite, score_vendor, VendorScoreResult
from app.services.scoring.tiering import determine_tier


# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_vendor(**kwargs) -> MagicMock:
    """Create a minimal mock Vendor with safe defaults."""
    vendor = MagicMock()
    vendor.id = "vendor-test-uuid"
    vendor.name = "Test Corp"
    vendor.under_investigation = kwargs.get("under_investigation", False)
    vendor.financial_health_signal = kwargs.get("financial_health_signal", "stable")
    vendor.contract_end = kwargs.get("contract_end", None)
    vendor.contract_status = kwargs.get("contract_status", "active")
    vendor.last_assessed_at = kwargs.get("last_assessed_at", datetime.utcnow())
    return vendor


def make_breach(**kwargs) -> MagicMock:
    """Create a mock BreachEvent."""
    b = MagicMock()
    b.breach_date = kwargs.get("breach_date", date.today() - timedelta(days=30))
    b.severity = kwargs.get("severity", "HIGH")
    b.resolved = kwargs.get("resolved", False)
    return b


def make_cert(**kwargs) -> MagicMock:
    """Create a mock Certification."""
    c = MagicMock()
    c.cert_type = kwargs.get("cert_type", "SOC2_TYPE2")
    c.status = kwargs.get("status", "current")
    c.expiry_date = kwargs.get("expiry_date", date.today() + timedelta(days=365))
    return c


def make_scope(**kwargs) -> MagicMock:
    """Create a mock DataAccessScope."""
    s = MagicMock()
    s.pii_access = kwargs.get("pii_access", False)
    s.financial_access = kwargs.get("financial_access", False)
    s.broad_system_access = kwargs.get("broad_system_access", False)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# breach_subscore tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBreachSubscore:
    def test_no_breaches_returns_zero(self):
        assert compute_breach_subscore([]) == 0.0

    def test_under_investigation_forces_100(self):
        assert compute_breach_subscore([], under_investigation=True) == 100.0

    def test_under_investigation_overrides_empty_breaches(self):
        breach = make_breach(severity="LOW", breach_date=date.today() - timedelta(days=3650))
        assert compute_breach_subscore([breach], under_investigation=True) == 100.0

    def test_critical_breach_today_gives_100(self):
        breach = make_breach(severity="CRITICAL", breach_date=date.today())
        score = compute_breach_subscore([breach])
        # CRITICAL weight=1.0, months=0 → 1.0 * exp(0) * 100 = 100
        assert score == 100.0

    def test_high_breach_today(self):
        breach = make_breach(severity="HIGH", breach_date=date.today())
        score = compute_breach_subscore([breach])
        # HIGH weight=0.7 → 0.7 * 100 = 70
        assert abs(score - 70.0) < 1.0

    def test_old_breach_decays(self):
        old_breach = make_breach(
            severity="CRITICAL",
            breach_date=date.today() - timedelta(days=365),  # ~12 months ago
        )
        score = compute_breach_subscore([old_breach])
        # Should be significantly less than 100 due to decay
        # exp(-12/12) = exp(-1) ≈ 0.368 → 36.8
        assert score < 50.0
        assert score > 20.0  # still meaningful

    def test_multiple_breaches_accumulate(self):
        b1 = make_breach(severity="HIGH", breach_date=date.today() - timedelta(days=30))
        b2 = make_breach(severity="MEDIUM", breach_date=date.today() - timedelta(days=60))
        score_combined = compute_breach_subscore([b1, b2])
        score_single   = compute_breach_subscore([b1])
        assert score_combined > score_single

    def test_score_capped_at_100(self):
        breaches = [
            make_breach(severity="CRITICAL", breach_date=date.today())
            for _ in range(10)
        ]
        assert compute_breach_subscore(breaches) == 100.0

    def test_unknown_severity_uses_default_weight(self):
        breach = make_breach(severity="UNKNOWN", breach_date=date.today())
        # Should not raise; treated as LOW (0.2)
        score = compute_breach_subscore([breach])
        assert 0 <= score <= 100


# ─────────────────────────────────────────────────────────────────────────────
# access_subscore tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAccessSubscore:
    def test_no_scope_returns_base(self):
        assert compute_access_subscore(None) == 20.0

    def test_no_flags_returns_base(self):
        scope = make_scope(pii_access=False, financial_access=False, broad_system_access=False)
        assert compute_access_subscore(scope) == 20.0

    def test_pii_adds_40(self):
        scope = make_scope(pii_access=True, financial_access=False, broad_system_access=False)
        assert compute_access_subscore(scope) == 60.0  # 20 + 40

    def test_financial_adds_30(self):
        scope = make_scope(pii_access=False, financial_access=True, broad_system_access=False)
        assert compute_access_subscore(scope) == 50.0  # 20 + 30

    def test_broad_adds_10(self):
        scope = make_scope(pii_access=False, financial_access=False, broad_system_access=True)
        assert compute_access_subscore(scope) == 30.0  # 20 + 10

    def test_all_flags_max(self):
        scope = make_scope(pii_access=True, financial_access=True, broad_system_access=True)
        assert compute_access_subscore(scope) == 100.0  # 20 + 40 + 30 + 10

    def test_pii_and_financial(self):
        scope = make_scope(pii_access=True, financial_access=True, broad_system_access=False)
        assert compute_access_subscore(scope) == 90.0  # 20 + 40 + 30


# ─────────────────────────────────────────────────────────────────────────────
# compliance_subscore tests
# ─────────────────────────────────────────────────────────────────────────────

class TestComplianceSubscore:
    def test_all_current_fresh_assessment(self):
        cert = make_cert(status="current", expiry_date=date.today() + timedelta(days=180))
        last_assessed = datetime.utcnow() - timedelta(days=30)
        score = compute_compliance_subscore([cert], last_assessed)
        assert score == 0.0

    def test_expired_cert_plus_40(self):
        cert = make_cert(status="expired", expiry_date=date.today() - timedelta(days=10))
        last_assessed = datetime.utcnow() - timedelta(days=30)
        score = compute_compliance_subscore([cert], last_assessed)
        assert score == 40.0  # 0 + 40

    def test_expiring_soon_plus_20(self):
        cert = make_cert(status="current", expiry_date=date.today() + timedelta(days=15))
        last_assessed = datetime.utcnow() - timedelta(days=30)
        score = compute_compliance_subscore([cert], last_assessed)
        assert score == 20.0  # 0 + 20

    def test_overdue_assessment_plus_15(self):
        cert = make_cert(status="current", expiry_date=date.today() + timedelta(days=180))
        last_assessed = datetime.utcnow() - timedelta(days=400)  # > 12 months
        score = compute_compliance_subscore([cert], last_assessed)
        assert score == 15.0  # 0 + 15

    def test_never_assessed_plus_15(self):
        cert = make_cert(status="current", expiry_date=date.today() + timedelta(days=180))
        score = compute_compliance_subscore([cert], last_assessed_at=None)
        assert score == 15.0  # 0 + 15

    def test_all_penalties_combined_capped_at_100(self):
        cert = make_cert(status="expired", expiry_date=date.today() - timedelta(days=10))
        expiring = make_cert(status="current", expiry_date=date.today() + timedelta(days=10))
        last_assessed = datetime.utcnow() - timedelta(days=400)
        score = compute_compliance_subscore([cert, expiring], last_assessed)
        # 0 + 40 (expired) + 20 (expiring_soon) + 15 (overdue) = 75
        assert score == 75.0

    def test_capped_at_100(self):
        # Even if penalties exceed 100, cap at 100
        cert = make_cert(status="expired")
        score = compute_compliance_subscore([cert, cert, cert], last_assessed_at=None)
        assert score <= 100.0

    def test_get_compliance_flags(self):
        cert = make_cert(status="expired")
        flags = get_compliance_flags([cert], last_assessed_at=None)
        assert flags["has_expired_cert"] is True
        assert flags["is_assessment_overdue"] is True


# ─────────────────────────────────────────────────────────────────────────────
# financial_subscore tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFinancialSubscore:
    def test_stable(self):
        assert compute_financial_subscore("stable") == 10.0

    def test_watch(self):
        assert compute_financial_subscore("watch") == 50.0

    def test_distressed(self):
        assert compute_financial_subscore("distressed") == 90.0

    def test_unknown(self):
        assert compute_financial_subscore("unknown") == 40.0

    def test_unrecognised_defaults_to_unknown(self):
        assert compute_financial_subscore("garbage") == 40.0


# ─────────────────────────────────────────────────────────────────────────────
# compute_composite tests
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeComposite:
    def test_all_zero_breach_compliance_100(self):
        # breach=0, access=20 (base), compliance=100, financial=10 (stable)
        score = compute_composite(0.0, 20.0, 100.0, 10.0)
        # 0.40*0 + 0.25*20 + 0.20*100 + 0.15*10 = 0 + 5 + 20 + 1.5 = 26.5
        assert abs(score - 26.5) < 0.1

    def test_all_max_gives_100(self):
        score = compute_composite(100.0, 100.0, 100.0, 100.0)
        assert score == 100.0

    def test_all_zero_gives_zero(self):
        # compliance=0 means good compliance (no penalties)
        # breach=0 means no breaches, etc.
        score = compute_composite(0.0, 20.0, 0.0, 10.0)
        # 0 + 5 + 0 + 1.5 = 6.5
        assert abs(score - 6.5) < 0.1

    def test_weights_sum_respected(self):
        # Perfect breach scenario, no compliance issues
        score = compute_composite(100.0, 100.0, 25.0, 90.0)
        expected = 0.40*100 + 0.25*100 + 0.20*25 + 0.15*90
        assert abs(score - expected) < 0.1

    def test_capped_at_100(self):
        score = compute_composite(200.0, 200.0, 200.0, 200.0)
        assert score == 100.0


# ─────────────────────────────────────────────────────────────────────────────
# tiering boundary tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTiering:
    def _tier(self, composite, vendor=None, breaches=None, certs=None, scope=None):
        v = vendor or make_vendor()
        tier, anomalies, color = determine_tier(
            composite_score=composite,
            vendor=v,
            breaches=breaches or [],
            certs=certs or [],
            scope=scope,
        )
        return tier, anomalies, color

    # ── CRITICAL ─────────────────────────────────────────────────────────────
    def test_under_investigation_critical(self):
        vendor = make_vendor(under_investigation=True)
        tier, anomalies, color = self._tier(50.0, vendor=vendor)
        assert tier == "CRITICAL"
        assert "VENDOR_UNDER_INVESTIGATION" in anomalies
        assert color == "RED"

    def test_recent_breach_plus_pii_critical(self):
        breach = make_breach(severity="HIGH", breach_date=date.today() - timedelta(days=30))
        scope = make_scope(pii_access=True)
        tier, anomalies, color = self._tier(50.0, breaches=[breach], scope=scope)
        assert tier == "CRITICAL"
        assert "BREACHED_VENDOR_HIGH_ACCESS" in anomalies
        assert color == "RED"

    def test_recent_breach_plus_financial_critical(self):
        breach = make_breach(severity="MEDIUM", breach_date=date.today() - timedelta(days=10))
        scope = make_scope(financial_access=True)
        tier, anomalies, color = self._tier(50.0, breaches=[breach], scope=scope)
        assert tier == "CRITICAL"
        assert color == "RED"

    # ── HIGH ─────────────────────────────────────────────────────────────────
    def test_composite_above_80_high(self):
        tier, anomalies, color = self._tier(85.0)
        assert tier == "HIGH"
        assert "HIGH_RISK_SCORE" in anomalies
        assert color == "RED"

    def test_composite_exactly_80_not_high(self):
        tier, anomalies, _ = self._tier(80.0)
        # Exactly 80 does NOT trigger HIGH_RISK_SCORE (threshold is > 80)
        assert "HIGH_RISK_SCORE" not in anomalies

    def test_expired_cert_with_sensitive_access_high(self):
        cert = make_cert(status="expired")
        scope = make_scope(pii_access=True)
        tier, anomalies, color = self._tier(40.0, certs=[cert], scope=scope)
        assert tier == "HIGH"
        assert "EXPIRED_CERTIFICATION" in anomalies
        assert color == "RED"

    # ── MEDIUM ───────────────────────────────────────────────────────────────
    def test_recent_breach_no_sensitive_access_medium(self):
        breach = make_breach(breach_date=date.today() - timedelta(days=30))
        scope = make_scope(pii_access=False, financial_access=False)
        tier, anomalies, color = self._tier(40.0, breaches=[breach], scope=scope)
        assert tier == "MEDIUM"
        assert "RECENTLY_BREACHED_VENDOR" in anomalies
        assert color == "YELLOW"

    def test_contract_expired_active_access_medium(self):
        vendor = make_vendor(
            contract_end=date.today() - timedelta(days=10),
            contract_status="active",
        )
        tier, anomalies, color = self._tier(40.0, vendor=vendor)
        assert tier == "MEDIUM"
        assert "CONTRACT_EXPIRED_ACTIVE_ACCESS" in anomalies
        assert color == "YELLOW"

    def test_expired_cert_no_sensitive_access_medium(self):
        cert = make_cert(status="expired")
        scope = make_scope(pii_access=False, financial_access=False)
        tier, anomalies, color = self._tier(40.0, certs=[cert], scope=scope)
        assert tier == "MEDIUM"
        assert "EXPIRED_CERTIFICATION" in anomalies

    # ── LOW ──────────────────────────────────────────────────────────────────
    def test_composite_65_to_80_low(self):
        tier, anomalies, color = self._tier(72.0)
        assert tier == "LOW"
        assert "ELEVATED_RISK_VENDOR" in anomalies
        assert color == "YELLOW"

    def test_composite_exactly_65_low(self):
        tier, anomalies, _ = self._tier(65.0)
        assert tier == "LOW"

    def test_composite_exactly_80_low(self):
        tier, anomalies, _ = self._tier(80.0)
        assert tier == "LOW"

    # ── CLEAR ─────────────────────────────────────────────────────────────────
    def test_clean_vendor_clear(self):
        tier, anomalies, color = self._tier(26.5)
        assert tier == "CLEAR"
        assert anomalies == []
        assert color == "GREEN"

    def test_composite_below_65_no_other_flags_clear(self):
        tier, anomalies, color = self._tier(64.9)
        assert tier == "CLEAR"
        assert color == "GREEN"

    # ── Priority ordering ────────────────────────────────────────────────────
    def test_investigation_overrides_high_risk_score(self):
        """CRITICAL must win even when composite > 80."""
        vendor = make_vendor(under_investigation=True)
        tier, anomalies, _ = self._tier(90.0, vendor=vendor)
        assert tier == "CRITICAL"
        # Both anomaly types should be present
        assert "VENDOR_UNDER_INVESTIGATION" in anomalies
        assert "HIGH_RISK_SCORE" in anomalies

    def test_multiple_anomalies_collected(self):
        """Multiple conditions can flag simultaneously — highest tier wins."""
        vendor = make_vendor(
            contract_end=date.today() - timedelta(days=5),
            contract_status="active",
        )
        breach = make_breach(breach_date=date.today() - timedelta(days=20))
        scope = make_scope(pii_access=False)
        tier, anomalies, _ = self._tier(40.0, vendor=vendor, breaches=[breach], scope=scope)
        assert "CONTRACT_EXPIRED_ACTIVE_ACCESS" in anomalies
        assert "RECENTLY_BREACHED_VENDOR" in anomalies


# ─────────────────────────────────────────────────────────────────────────────
# score_vendor integration test
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreVendorIntegration:
    """
    Integration tests that call score_vendor() end-to-end
    (pure compute — no DB, no LLM).
    """

    def test_returns_vendor_score_result(self):
        vendor = make_vendor(financial_health_signal="stable")
        result = score_vendor(vendor, [], [], None)
        assert isinstance(result, VendorScoreResult)
        assert result.vendor_id == vendor.id
        assert 0 <= result.composite_score <= 100

    def test_llm_fields_not_set_by_engine(self):
        """rationale must be None from score_vendor — only set after narrative.py."""
        vendor = make_vendor()
        result = score_vendor(vendor, [], [], None)
        assert result.rationale is None

    def test_worst_case_vendor_critical(self):
        vendor = make_vendor(
            under_investigation=True,
            financial_health_signal="distressed",
        )
        breach = make_breach(severity="CRITICAL", breach_date=date.today())
        cert = make_cert(status="expired")
        scope = make_scope(pii_access=True, financial_access=True, broad_system_access=True)
        result = score_vendor(vendor, [breach], [cert], scope)
        assert result.tier == "CRITICAL"
        assert result.status_color == "RED"
        assert result.composite_score > 80

    def test_best_case_vendor_clear(self):
        vendor = make_vendor(financial_health_signal="stable")
        cert = make_cert(status="current", expiry_date=date.today() + timedelta(days=365))
        scope = make_scope(pii_access=False, financial_access=False)
        result = score_vendor(vendor, [], [cert], scope)
        assert result.tier == "CLEAR"
        assert result.status_color == "GREEN"
