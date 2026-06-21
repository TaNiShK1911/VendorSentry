"""
Tests for breach-to-vendor matching logic.

Covers:
    - Exact domain match (confidence 1.0)
    - No match at all (empty list)
    - Fuzzy match above 0.85 threshold
    - Near-miss below threshold (correctly excluded)
    - Vendor with no website_domain (falls through to fuzzy-only)
"""
import pytest
from unittest.mock import MagicMock

from app.services.monitoring.breach_sources.matcher import (
    match_vendor_to_breaches,
    BreachMatch,
    _FUZZY_THRESHOLD,
)


def _make_vendor(name: str, website_domain: str | None = None) -> MagicMock:
    """Create a mock Vendor with the fields matcher.py needs."""
    vendor = MagicMock()
    vendor.name = name
    vendor.website_domain = website_domain
    return vendor


# --------------------------------------------------------------------------- #
# Fixture: sample HIBP catalog entries
# --------------------------------------------------------------------------- #

CATALOG = [
    {
        "Name": "Adobe",
        "Title": "Adobe",
        "Domain": "adobe.com",
        "BreachDate": "2013-10-04",
        "PwnCount": 152445165,
        "DataClasses": ["Email addresses", "Passwords", "Usernames"],
        "IsVerified": True,
        "IsSensitive": False,
    },
    {
        "Name": "Dropbox",
        "Title": "Dropbox",
        "Domain": "dropbox.com",
        "BreachDate": "2012-07-01",
        "PwnCount": 68648009,
        "DataClasses": ["Email addresses", "Passwords"],
        "IsVerified": True,
        "IsSensitive": False,
    },
    {
        "Name": "LinkedIn",
        "Title": "LinkedIn",
        "Domain": "linkedin.com",
        "BreachDate": "2012-05-05",
        "PwnCount": 164611595,
        "DataClasses": ["Email addresses", "Passwords"],
        "IsVerified": True,
        "IsSensitive": False,
    },
    {
        "Name": "AcmeDataBreach2024",
        "Title": "Acme Data Systems Inc",
        "Domain": "",  # no domain
        "BreachDate": "2024-03-15",
        "PwnCount": 5000000,
        "DataClasses": ["Email addresses", "Usernames"],
        "IsVerified": True,
        "IsSensitive": False,
    },
]


class TestDomainMatch:
    """Tests for the domain-based matching path."""

    def test_exact_domain_match(self):
        vendor = _make_vendor("Adobe Inc.", website_domain="adobe.com")
        matches = match_vendor_to_breaches(vendor, CATALOG)

        assert len(matches) == 1
        assert matches[0].match_type == "domain"
        assert matches[0].confidence == 1.0
        assert matches[0].breach["Name"] == "Adobe"

    def test_domain_match_case_insensitive(self):
        vendor = _make_vendor("Dropbox", website_domain="DROPBOX.COM")
        matches = match_vendor_to_breaches(vendor, CATALOG)

        assert len(matches) == 1
        assert matches[0].match_type == "domain"
        assert matches[0].breach["Name"] == "Dropbox"

    def test_domain_match_suppresses_fuzzy(self):
        """When domain matches exist, fuzzy matches should not be returned."""
        vendor = _make_vendor("Adobe", website_domain="adobe.com")
        matches = match_vendor_to_breaches(vendor, CATALOG)

        # Should have exactly the domain match, no fuzzy
        assert all(m.match_type == "domain" for m in matches)


class TestNoMatch:
    """Tests for when no match should be found."""

    def test_no_match_different_domain(self):
        vendor = _make_vendor("Totally Unrelated Corp", website_domain="unrelated.com")
        matches = match_vendor_to_breaches(vendor, CATALOG)
        assert len(matches) == 0

    def test_no_match_empty_catalog(self):
        vendor = _make_vendor("Adobe", website_domain="adobe.com")
        matches = match_vendor_to_breaches(vendor, [])
        assert len(matches) == 0


class TestFuzzyMatch:
    """Tests for the fuzzy name-matching path."""

    def test_fuzzy_match_above_threshold(self):
        """'Acme Data Systems' should fuzzy-match 'Acme Data Systems Inc'."""
        vendor = _make_vendor("Acme Data Systems", website_domain=None)
        matches = match_vendor_to_breaches(vendor, CATALOG)

        # Should find the AcmeDataBreach2024 entry via fuzzy matching
        fuzzy_matches = [m for m in matches if m.match_type == "fuzzy_name"]
        assert len(fuzzy_matches) >= 1
        assert fuzzy_matches[0].confidence >= _FUZZY_THRESHOLD
        assert fuzzy_matches[0].confidence < 1.0

    def test_fuzzy_match_below_threshold_excluded(self):
        """'SomeRandom Corp' should NOT fuzzy-match any breach."""
        vendor = _make_vendor("SomeRandom Corp That Doesn't Match Anything", website_domain=None)
        matches = match_vendor_to_breaches(vendor, CATALOG)
        assert len(matches) == 0

    def test_near_miss_excluded(self):
        """A name that's similar but below threshold should not match."""
        # "Adob" is close to "Adobe" but not close enough (we want to ensure no match)
        # Actually "Adob" to "Adobe" is 0.88, which is above 0.85.
        # Let's use "Ado" to "Adobe": length 3 vs 5. Ratio = 6/8 = 0.75 < 0.85
        vendor = _make_vendor("Ado", website_domain=None)
        matches = match_vendor_to_breaches(vendor, CATALOG)

        # Should be excluded
        assert len(matches) == 0


class TestVendorWithoutDomain:
    """Tests for vendors that have no website_domain set."""

    def test_no_domain_falls_to_fuzzy(self):
        """A vendor with no website_domain should still attempt fuzzy matching."""
        vendor = _make_vendor("LinkedIn", website_domain=None)
        matches = match_vendor_to_breaches(vendor, CATALOG)

        # Should find LinkedIn via fuzzy name match
        assert len(matches) >= 1
        # Since domain is None, these should all be fuzzy matches
        for m in matches:
            assert m.match_type == "fuzzy_name"

    def test_no_domain_no_fuzzy_match(self):
        """A vendor with no domain and an unrelated name should return nothing."""
        vendor = _make_vendor("Completely Different Name XYZ", website_domain=None)
        matches = match_vendor_to_breaches(vendor, CATALOG)
        assert len(matches) == 0
