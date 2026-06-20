"""
Unit tests for the conflict checker.

Verifies that LLM-claimed values that disagree with stored DB fields
produce ConflictRecord entries — never silent resolution.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.services.extraction.conflict_checker import check_conflicts
from app.schemas.extraction import ConflictRecord


def make_cert(cert_type="SOC2_TYPE2", status="current", expiry_date=None):
    c = MagicMock()
    c.cert_type = cert_type
    c.status = status
    c.expiry_date = expiry_date or date.today() + timedelta(days=180)
    return c


def make_scope(pii_access=False, financial_access=False):
    s = MagicMock()
    s.pii_access = pii_access
    s.financial_access = financial_access
    return s


class TestConflictChecker:

    # ── No conflicts ─────────────────────────────────────────────────────────

    def test_no_conflicts_when_data_matches(self):
        cert = make_cert(cert_type="SOC2_TYPE2", status="current")
        extracted = {
            "data_access": {"pii": False, "financial": False, "systems": []},
            "compliance_claims": [{"type": "SOC2_TYPE2", "claimed_status": "current"}],
            "sla_terms": {},
            "conflicts": [],
        }
        scope = make_scope(pii_access=False, financial_access=False)
        result = check_conflicts(extracted, [cert], scope)
        assert result == []

    def test_empty_extraction_no_conflicts(self):
        extracted = {
            "data_access": {}, "compliance_claims": [],
            "sla_terms": {}, "conflicts": [],
        }
        result = check_conflicts(extracted, [], None)
        assert result == []

    # ── Cert status conflict ──────────────────────────────────────────────────

    def test_cert_status_conflict_detected(self):
        """LLM claims SOC2 is current but DB shows expired."""
        cert = make_cert(cert_type="SOC2_TYPE2", status="expired")
        extracted = {
            "compliance_claims": [{"type": "SOC2_TYPE2", "claimed_status": "current"}],
        }
        result = check_conflicts(extracted, [cert], None)
        assert len(result) == 1
        conflict = result[0]
        assert conflict.field == "certifications.SOC2_TYPE2.status"
        assert conflict.claimed == "current"
        assert conflict.actual_on_record == "expired"

    def test_cert_status_conflict_not_resolved(self):
        """Both sides must be recorded — no silent winner."""
        cert = make_cert(cert_type="ISO_27001", status="expired")
        extracted = {
            "compliance_claims": [{"type": "ISO_27001", "claimed_status": "current"}],
        }
        result = check_conflicts(extracted, [cert], None)
        assert any(c.claimed == "current" for c in result)
        assert any(c.actual_on_record == "expired" for c in result)

    # ── Cert expiry date conflict ─────────────────────────────────────────────

    def test_expiry_date_conflict_detected(self):
        existing_expiry = date.today() + timedelta(days=60)
        claimed_expiry  = date.today() + timedelta(days=180)
        cert = make_cert(cert_type="SOC2_TYPE2", status="current", expiry_date=existing_expiry)
        extracted = {
            "compliance_claims": [{
                "type": "SOC2_TYPE2",
                "claimed_status": "current",
                "claimed_expiry": str(claimed_expiry),
            }],
        }
        result = check_conflicts(extracted, [cert], None)
        date_conflicts = [c for c in result if "expiry_date" in c.field]
        assert len(date_conflicts) == 1
        assert date_conflicts[0].claimed == str(claimed_expiry)
        assert date_conflicts[0].actual_on_record == str(existing_expiry)

    def test_matching_expiry_no_conflict(self):
        expiry = date.today() + timedelta(days=180)
        cert = make_cert(cert_type="SOC2_TYPE2", status="current", expiry_date=expiry)
        extracted = {
            "compliance_claims": [{
                "type": "SOC2_TYPE2",
                "claimed_status": "current",
                "claimed_expiry": str(expiry),
            }],
        }
        result = check_conflicts(extracted, [cert], None)
        assert result == []

    def test_invalid_date_string_skipped_gracefully(self):
        cert = make_cert(cert_type="SOC2_TYPE2", status="current")
        extracted = {
            "compliance_claims": [{
                "type": "SOC2_TYPE2",
                "claimed_status": "current",
                "claimed_expiry": "not-a-date",
            }],
        }
        # Should not raise
        result = check_conflicts(extracted, [cert], None)
        # No date conflict — bad date is skipped
        date_conflicts = [c for c in result if "expiry_date" in c.field]
        assert date_conflicts == []

    # ── Unknown cert conflict ─────────────────────────────────────────────────

    def test_unknown_cert_flagged(self):
        """LLM claims a cert type we have no record of."""
        extracted = {
            "compliance_claims": [{"type": "PCI_DSS", "claimed_status": "current"}],
        }
        result = check_conflicts(extracted, [], None)  # no certs on record
        assert len(result) == 1
        assert "PCI_DSS" in result[0].field
        assert result[0].actual_on_record is None

    # ── PII access conflict ───────────────────────────────────────────────────

    def test_pii_access_conflict_detected(self):
        """LLM claims no PII but DB shows PII access."""
        scope = make_scope(pii_access=True, financial_access=False)
        extracted = {
            "data_access": {"pii": False, "financial": False, "systems": []},
            "compliance_claims": [],
        }
        result = check_conflicts(extracted, [], scope)
        pii_conflicts = [c for c in result if "pii_access" in c.field]
        assert len(pii_conflicts) == 1
        assert pii_conflicts[0].claimed is False
        assert pii_conflicts[0].actual_on_record is True

    def test_financial_access_conflict_detected(self):
        scope = make_scope(pii_access=False, financial_access=True)
        extracted = {
            "data_access": {"pii": False, "financial": False, "systems": []},
            "compliance_claims": [],
        }
        result = check_conflicts(extracted, [], scope)
        fin_conflicts = [c for c in result if "financial_access" in c.field]
        assert len(fin_conflicts) == 1

    def test_no_scope_skips_access_check(self):
        """If scope is None in DB, no access conflicts can fire."""
        extracted = {
            "data_access": {"pii": True, "financial": True, "systems": []},
            "compliance_claims": [],
        }
        result = check_conflicts(extracted, [], None)
        access_conflicts = [c for c in result if "data_access" in c.field]
        assert access_conflicts == []

    # ── Multiple conflicts in one extraction ──────────────────────────────────

    def test_multiple_conflicts_all_returned(self):
        cert = make_cert(cert_type="SOC2_TYPE2", status="expired")
        scope = make_scope(pii_access=True)
        extracted = {
            "data_access": {"pii": False, "financial": False, "systems": []},
            "compliance_claims": [{"type": "SOC2_TYPE2", "claimed_status": "current"}],
        }
        result = check_conflicts(extracted, [cert], scope)
        # Expect: cert status conflict + pii access conflict
        assert len(result) >= 2
        fields = [c.field for c in result]
        assert any("SOC2_TYPE2.status" in f for f in fields)
        assert any("pii_access" in f for f in fields)
