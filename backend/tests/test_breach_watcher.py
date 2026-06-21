"""
Tests for breach_watcher.py — the Celery task that polls HIBP.

Covers:
    - Domain match creates exactly one BreachEvent + triggers rescore with rationale
    - Fuzzy match creates EvidenceSignal but NOT a BreachEvent, no rescore
    - Dedup: polling twice with same catalog doesn't create duplicate BreachEvent rows
    - No match: vendor with unrelated domain → nothing created

All HTTP calls are mocked — no real network access.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.monitoring.breach_watcher import poll_breach_db
from app.models import Vendor, VendorScore, EvidenceSignal, BreachEvent


# --------------------------------------------------------------------------- #
# Fixture: sample HIBP catalog entries
# --------------------------------------------------------------------------- #

SAMPLE_CATALOG = [
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
        "Name": "SomeSpamList",
        "Title": "Some Spam List",
        "Domain": "",
        "BreachDate": "2023-01-01",
        "PwnCount": 100,
        "DataClasses": [],
        "IsVerified": False,
        "IsSensitive": False,
    },
]


@pytest.fixture
def vendor_with_domain(db_session):
    """Vendor whose domain matches 'adobe.com' in the catalog."""
    vendor = Vendor(
        id="vendor-adobe",
        name="Adobe Systems Inc",
        website_domain="adobe.com",
    )
    db_session.add(vendor)
    db_session.commit()
    return vendor


@pytest.fixture
def vendor_fuzzy(db_session):
    """Vendor whose name fuzzy-matches a catalog entry but has no domain."""
    vendor = Vendor(
        id="vendor-fuzzy-adobe",
        name="Adobe",
        website_domain=None,
    )
    db_session.add(vendor)
    db_session.commit()
    return vendor


@pytest.fixture
def vendor_no_match(db_session):
    """Vendor with no domain or name match."""
    vendor = Vendor(
        id="vendor-unrelated",
        name="Totally Unrelated Corp",
        website_domain="unrelated.example.com",
    )
    db_session.add(vendor)
    db_session.commit()
    return vendor


class TestDomainMatchFlow:
    """Domain match → BreachEvent + rescore + alert."""

    def test_domain_match_creates_breach_event(self, db_session, vendor_with_domain):
        with patch("app.services.monitoring.breach_watcher.fetch_breach_catalog", return_value=SAMPLE_CATALOG), \
             patch("app.services.monitoring.breach_watcher.SessionLocal", return_value=db_session), \
             patch("app.services.monitoring.breach_watcher.create_new_breach_alert") as mock_alert:

            result = poll_breach_db()

        # Should have created exactly one BreachEvent
        breaches = db_session.query(BreachEvent).filter_by(vendor_id="vendor-adobe").all()
        assert len(breaches) == 1
        assert breaches[0].external_id == "Adobe"
        assert breaches[0].source == "hibp"
        assert breaches[0].severity == "CRITICAL"  # passwords + 152M records

        # Should have created a VendorScore (rescore triggered)
        scores = db_session.query(VendorScore).filter_by(vendor_id="vendor-adobe").all()
        assert len(scores) == 1
        assert scores[0].triggered_by == "breach_detected"
        assert scores[0].rationale is not None

        # Should have created an EvidenceSignal with consumed_by_score_id set
        signal = db_session.query(EvidenceSignal).filter_by(
            vendor_id="vendor-adobe", signal_type="new_breach"
        ).first()
        assert signal is not None
        assert signal.consumed_by_score_id == scores[0].id

        # Should have triggered an alert
        mock_alert.assert_called_once()

        assert "1 new breaches detected" in result


class TestFuzzyMatchFlow:
    """Fuzzy match → EvidenceSignal only, no BreachEvent, no rescore."""

    def test_fuzzy_match_creates_signal_not_breach(self, db_session, vendor_fuzzy):
        with patch("app.services.monitoring.breach_watcher.fetch_breach_catalog", return_value=SAMPLE_CATALOG), \
             patch("app.services.monitoring.breach_watcher.SessionLocal", return_value=db_session), \
             patch("app.services.monitoring.breach_watcher.create_new_breach_alert") as mock_alert:

            result = poll_breach_db()

        # Should NOT have created a BreachEvent
        breaches = db_session.query(BreachEvent).filter_by(vendor_id="vendor-fuzzy-adobe").all()
        assert len(breaches) == 0

        # Should NOT have created a VendorScore
        scores = db_session.query(VendorScore).filter_by(vendor_id="vendor-fuzzy-adobe").all()
        assert len(scores) == 0

        # Should have created a fuzzy_breach_match EvidenceSignal
        signals = db_session.query(EvidenceSignal).filter_by(
            vendor_id="vendor-fuzzy-adobe", signal_type="fuzzy_breach_match"
        ).all()
        assert len(signals) >= 1
        assert signals[0].payload["match_type"] == "fuzzy_name"

        # No alert for fuzzy matches
        mock_alert.assert_not_called()

        assert "fuzzy matches flagged for review" in result


class TestDedup:
    """Polling twice with same catalog should not create duplicate BreachEvents."""

    def test_no_duplicate_breach_events(self, db_session, vendor_with_domain):
        with patch("app.services.monitoring.breach_watcher.fetch_breach_catalog", return_value=SAMPLE_CATALOG), \
             patch("app.services.monitoring.breach_watcher.SessionLocal", return_value=db_session), \
             patch("app.services.monitoring.breach_watcher.create_new_breach_alert"):

            # First poll
            poll_breach_db()

            # Second poll with same catalog
            result = poll_breach_db()

        # Should still have exactly one BreachEvent
        breaches = db_session.query(BreachEvent).filter_by(vendor_id="vendor-adobe").all()
        assert len(breaches) == 1

        # Second poll should report 0 new breaches
        assert "0 new breaches detected" in result


class TestNoMatch:
    """Vendor with no match → nothing created."""

    def test_no_match_creates_nothing(self, db_session, vendor_no_match):
        with patch("app.services.monitoring.breach_watcher.fetch_breach_catalog", return_value=SAMPLE_CATALOG), \
             patch("app.services.monitoring.breach_watcher.SessionLocal", return_value=db_session), \
             patch("app.services.monitoring.breach_watcher.create_new_breach_alert") as mock_alert:

            result = poll_breach_db()

        breaches = db_session.query(BreachEvent).filter_by(vendor_id="vendor-unrelated").all()
        assert len(breaches) == 0

        signals = db_session.query(EvidenceSignal).filter_by(vendor_id="vendor-unrelated").all()
        assert len(signals) == 0

        mock_alert.assert_not_called()
        assert "0 new breaches detected" in result


class TestEmptyCatalog:
    """When the catalog is empty, nothing should happen."""

    def test_empty_catalog_skips(self, db_session, vendor_with_domain):
        with patch("app.services.monitoring.breach_watcher.fetch_breach_catalog", return_value=[]), \
             patch("app.services.monitoring.breach_watcher.SessionLocal", return_value=db_session):

            result = poll_breach_db()

        assert "no catalog available" in result
