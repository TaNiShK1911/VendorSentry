"""
Tests for SEC EDGAR public records enrichment.

Covers:
    - Filing match found → EvidenceSignal with source="public_records", signal_type="regulatory_filing"
    - No match → no signal created (honest result)
    - Malformed response → graceful handling, no crash
    - Rate limiting: recent check skips vendor

All HTTP calls are mocked — no real network access to sec.gov.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.services.enrichment.public_records import check_public_records
from app.models import Vendor, EvidenceSignal


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

SAMPLE_EDGAR_RESPONSE_WITH_HITS = {
    "hits": {
        "hits": [
            {
                "_source": {
                    "form_type": "8-K",
                    "file_date": "2024-06-15",
                    "entity_name": "ADOBE INC",
                    "file_num": "001-12345",
                    "accession_no": "0001234567-24-001234",
                    "entity_id": "796343",
                }
            },
            {
                "_source": {
                    "form_type": "8-K",
                    "file_date": "2024-03-01",
                    "entity_name": "ADOBE INC",
                    "file_num": "001-12345",
                    "accession_no": "0001234567-24-000567",
                    "entity_id": "796343",
                }
            },
        ]
    }
}

SAMPLE_EDGAR_RESPONSE_NO_HITS = {
    "hits": {
        "hits": []
    }
}


@pytest.fixture
def vendor_public(db_session):
    """A public company vendor."""
    vendor = Vendor(
        id="vendor-adobe-sec",
        name="Adobe Inc",
    )
    db_session.add(vendor)
    db_session.commit()
    return vendor


@pytest.fixture
def vendor_private(db_session):
    """A private company vendor (no SEC filings expected)."""
    vendor = Vendor(
        id="vendor-private",
        name="Small Private Vendor LLC",
    )
    db_session.add(vendor)
    db_session.commit()
    return vendor


class TestFilingFound:
    """When SEC EDGAR returns matching filings."""

    def test_creates_evidence_signal(self, db_session, vendor_public):
        with patch("app.services.enrichment.public_records.httpx.get") as mock_get, \
             patch("app.services.enrichment.public_records.SessionLocal", return_value=db_session):

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = SAMPLE_EDGAR_RESPONSE_WITH_HITS
            mock_get.return_value = mock_resp

            result = check_public_records()

        # Should have created a regulatory_filing EvidenceSignal
        signals = db_session.query(EvidenceSignal).filter_by(
            vendor_id="vendor-adobe-sec",
            source="public_records",
            signal_type="regulatory_filing",
        ).all()
        assert len(signals) == 1

        payload = signals[0].payload
        assert payload["filing_count"] == 2
        assert len(payload["filings"]) == 2
        assert payload["filings"][0]["form_type"] == "8-K"
        assert "1 signals generated" in result

    def test_user_agent_included(self, db_session, vendor_public):
        with patch("app.services.enrichment.public_records.httpx.get") as mock_get, \
             patch("app.services.enrichment.public_records.SessionLocal", return_value=db_session):

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = SAMPLE_EDGAR_RESPONSE_NO_HITS
            mock_get.return_value = mock_resp

            check_public_records()

        # Verify User-Agent header was set
        call_kwargs = mock_get.call_args
        assert "User-Agent" in call_kwargs.kwargs.get("headers", {})


class TestNoMatch:
    """When SEC EDGAR returns no matching filings."""

    def test_no_signal_created(self, db_session, vendor_private):
        with patch("app.services.enrichment.public_records.httpx.get") as mock_get, \
             patch("app.services.enrichment.public_records.SessionLocal", return_value=db_session):

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = SAMPLE_EDGAR_RESPONSE_NO_HITS
            mock_get.return_value = mock_resp

            result = check_public_records()

        # Should NOT have created any signal — no fabricated results
        signals = db_session.query(EvidenceSignal).filter_by(
            vendor_id="vendor-private",
        ).all()
        assert len(signals) == 0
        assert "0 signals generated" in result


class TestMalformedResponse:
    """Graceful handling of malformed SEC EDGAR responses."""

    def test_malformed_json(self, db_session, vendor_public):
        with patch("app.services.enrichment.public_records.httpx.get") as mock_get, \
             patch("app.services.enrichment.public_records.SessionLocal", return_value=db_session):

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.side_effect = ValueError("Malformed JSON")
            mock_get.return_value = mock_resp

            result = check_public_records()

        # Should not crash, no signals created
        signals = db_session.query(EvidenceSignal).filter_by(vendor_id="vendor-adobe-sec").all()
        assert len(signals) == 0

    def test_http_error(self, db_session, vendor_public):
        import httpx as httpx_mod

        with patch("app.services.enrichment.public_records.httpx.get") as mock_get, \
             patch("app.services.enrichment.public_records.SessionLocal", return_value=db_session):

            mock_get.side_effect = httpx_mod.ConnectTimeout("Timeout")

            result = check_public_records()

        # Should not crash
        signals = db_session.query(EvidenceSignal).filter_by(vendor_id="vendor-adobe-sec").all()
        assert len(signals) == 0

    def test_unexpected_response_shape(self, db_session, vendor_public):
        """Response is valid JSON but unexpected shape."""
        with patch("app.services.enrichment.public_records.httpx.get") as mock_get, \
             patch("app.services.enrichment.public_records.SessionLocal", return_value=db_session):

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {"unexpected": "shape"}
            mock_get.return_value = mock_resp

            result = check_public_records()

        # Unexpected shape → no filings extracted → no signal
        signals = db_session.query(EvidenceSignal).filter_by(vendor_id="vendor-adobe-sec").all()
        assert len(signals) == 0


class TestRateLimiting:
    """Skip vendors that were recently checked."""

    def test_skips_recently_checked_vendor(self, db_session, vendor_public):
        # Create a recent signal to simulate a prior check
        recent_signal = EvidenceSignal(
            vendor_id="vendor-adobe-sec",
            source="public_records",
            signal_type="regulatory_filing",
            payload={"note": "recent check"},
            received_at=datetime.utcnow() - timedelta(days=2),  # 2 days ago
        )
        db_session.add(recent_signal)
        db_session.commit()

        with patch("app.services.enrichment.public_records.httpx.get") as mock_get, \
             patch("app.services.enrichment.public_records.SessionLocal", return_value=db_session):

            result = check_public_records()

        # HTTP should not have been called — vendor was skipped
        mock_get.assert_not_called()
        assert "1 vendors skipped" in result
