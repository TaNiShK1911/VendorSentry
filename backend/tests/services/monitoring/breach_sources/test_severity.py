"""
Tests for severity inference from HIBP breach metadata.

Covers all four severity tiers (CRITICAL, HIGH, MEDIUM, LOW) plus
edge cases like empty DataClasses and missing PwnCount.
"""
import pytest

from app.services.monitoring.breach_sources.severity import infer_severity


class TestCriticalSeverity:
    """Breaches with sensitive data at massive scale → CRITICAL."""

    def test_passwords_and_high_pwncount(self):
        breach = {
            "DataClasses": ["Email addresses", "Passwords", "Usernames"],
            "PwnCount": 150_000_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "CRITICAL"

    def test_financial_data_and_high_pwncount(self):
        breach = {
            "DataClasses": ["Financial data", "Email addresses"],
            "PwnCount": 20_000_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "CRITICAL"

    def test_government_ids_and_high_pwncount(self):
        breach = {
            "DataClasses": ["Government issued IDs", "Names"],
            "PwnCount": 50_000_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "CRITICAL"

    def test_security_qa_and_high_pwncount(self):
        breach = {
            "DataClasses": ["Security questions and answers", "Email addresses"],
            "PwnCount": 12_000_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "CRITICAL"


class TestHighSeverity:
    """Sensitive data at smaller scale, or moderately sensitive data."""

    def test_passwords_below_critical_threshold(self):
        """Passwords present but below 10M — HIGH, not CRITICAL."""
        breach = {
            "DataClasses": ["Email addresses", "Passwords"],
            "PwnCount": 5_000_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "HIGH"

    def test_credit_cards(self):
        breach = {
            "DataClasses": ["Credit cards", "Email addresses"],
            "PwnCount": 500_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "HIGH"

    def test_sensitive_and_verified_flags(self):
        breach = {
            "DataClasses": ["Email addresses"],
            "PwnCount": 100_000,
            "IsVerified": True,
            "IsSensitive": True,
        }
        assert infer_severity(breach) == "HIGH"

    def test_auth_tokens(self):
        breach = {
            "DataClasses": ["Auth tokens"],
            "PwnCount": 50_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "HIGH"


class TestMediumSeverity:
    """Email/username-level data only, or verified moderate-scale breaches."""

    def test_email_addresses_only(self):
        breach = {
            "DataClasses": ["Email addresses"],
            "PwnCount": 1_000_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "MEDIUM"

    def test_usernames_and_ips(self):
        breach = {
            "DataClasses": ["Usernames", "IP addresses"],
            "PwnCount": 500_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "MEDIUM"

    def test_email_and_names(self):
        breach = {
            "DataClasses": ["Email addresses", "Names"],
            "PwnCount": 200_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "MEDIUM"


class TestLowSeverity:
    """Old, small, spam-list-adjacent, or unverified with no sensitive data."""

    def test_empty_data_classes(self):
        breach = {
            "DataClasses": [],
            "PwnCount": 100,
            "IsVerified": False,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "LOW"

    def test_missing_data_classes_key(self):
        breach = {
            "PwnCount": 50,
            "IsVerified": False,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "LOW"


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_missing_pwncount(self):
        """Missing PwnCount should not crash."""
        breach = {
            "DataClasses": ["Passwords"],
            "IsVerified": True,
            "IsSensitive": False,
        }
        # Passwords present but PwnCount=0 → HIGH (not CRITICAL)
        assert infer_severity(breach) == "HIGH"

    def test_pwncount_exactly_at_critical_threshold(self):
        """PwnCount exactly at 10M — still not CRITICAL (needs to be >10M)."""
        breach = {
            "DataClasses": ["Passwords"],
            "PwnCount": 10_000_000,
            "IsVerified": True,
            "IsSensitive": False,
        }
        # At threshold, not above — should be HIGH
        assert infer_severity(breach) == "HIGH"

    def test_pwncount_just_above_critical_threshold(self):
        breach = {
            "DataClasses": ["Passwords"],
            "PwnCount": 10_000_001,
            "IsVerified": True,
            "IsSensitive": False,
        }
        assert infer_severity(breach) == "CRITICAL"

    def test_output_matches_subscore_keys(self):
        """All outputs must match _SEVERITY_WEIGHTS keys exactly."""
        valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

        test_breaches = [
            {"DataClasses": ["Passwords"], "PwnCount": 100_000_000},
            {"DataClasses": ["Passwords"], "PwnCount": 1000},
            {"DataClasses": ["Email addresses"], "PwnCount": 1000},
            {"DataClasses": [], "PwnCount": 0},
        ]

        for breach in test_breaches:
            result = infer_severity(breach)
            assert result in valid_severities, f"Got {result!r} for {breach}"
