"""
Tests for the HIBP client — all HTTP calls are mocked.

Covers:
    - Successful fetch (latest breach + full catalog)
    - 403 response (missing User-Agent)
    - Connection timeout
    - Malformed JSON response
    - Conditional fetch caching (catalog reuse when latest unchanged)
    - Graceful degradation (never raises, returns cached or empty list)
"""
import pytest
from unittest.mock import patch, MagicMock

import httpx

from app.services.monitoring.breach_sources import hibp_client


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

SAMPLE_LATEST_BREACH = {
    "Name": "TestBreach2024",
    "Title": "Test Breach 2024",
    "Domain": "test.com",
    "BreachDate": "2024-01-15",
    "PwnCount": 1000000,
}

SAMPLE_CATALOG = [
    {
        "Name": "TestBreach2024",
        "Title": "Test Breach 2024",
        "Domain": "test.com",
        "BreachDate": "2024-01-15",
        "PwnCount": 1000000,
        "DataClasses": ["Email addresses", "Passwords"],
    },
    {
        "Name": "OlderBreach",
        "Title": "Older Breach",
        "Domain": "old.com",
        "BreachDate": "2020-06-01",
        "PwnCount": 500000,
        "DataClasses": ["Email addresses"],
    },
]


def _mock_response(json_data=None, status_code=200, text=""):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text

    if status_code >= 400:
        http_error = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
        resp.raise_for_status.side_effect = http_error
    else:
        resp.raise_for_status.return_value = None

    resp.json.return_value = json_data
    return resp


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the module-level cache before each test."""
    hibp_client._cached_catalog = []
    hibp_client._cached_latest_name = None
    yield
    hibp_client._cached_catalog = []
    hibp_client._cached_latest_name = None


# --------------------------------------------------------------------------- #
# fetch_latest_breach tests
# --------------------------------------------------------------------------- #

class TestFetchLatestBreach:

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_success(self, mock_get):
        mock_get.return_value = _mock_response(json_data=SAMPLE_LATEST_BREACH)
        result = hibp_client.fetch_latest_breach()

        assert result is not None
        assert result["Name"] == "TestBreach2024"
        mock_get.assert_called_once()

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_403_no_user_agent(self, mock_get):
        mock_get.return_value = _mock_response(status_code=403, text="Forbidden")
        result = hibp_client.fetch_latest_breach()

        assert result is None  # graceful degradation

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_timeout(self, mock_get):
        mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")
        result = hibp_client.fetch_latest_breach()

        assert result is None  # graceful degradation

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_malformed_json(self, mock_get):
        resp = _mock_response()
        resp.json.side_effect = ValueError("Malformed JSON")
        mock_get.return_value = resp
        result = hibp_client.fetch_latest_breach()

        assert result is None  # graceful degradation


# --------------------------------------------------------------------------- #
# fetch_breach_catalog tests
# --------------------------------------------------------------------------- #

class TestFetchBreachCatalog:

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_full_fetch_on_first_call(self, mock_get):
        """First call should fetch both latest breach and full catalog."""
        # First call returns latest breach, second returns full catalog
        mock_get.side_effect = [
            _mock_response(json_data=SAMPLE_LATEST_BREACH),
            _mock_response(json_data=SAMPLE_CATALOG),
        ]

        result = hibp_client.fetch_breach_catalog()

        assert len(result) == 2
        assert result[0]["Name"] == "TestBreach2024"
        assert mock_get.call_count == 2

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_cache_reuse_when_unchanged(self, mock_get):
        """Second call with same latest breach should reuse cache."""
        # First call: fetch both
        mock_get.side_effect = [
            _mock_response(json_data=SAMPLE_LATEST_BREACH),
            _mock_response(json_data=SAMPLE_CATALOG),
        ]
        result1 = hibp_client.fetch_breach_catalog()
        assert mock_get.call_count == 2

        # Second call: only check latest breach (cache hit)
        mock_get.reset_mock()
        mock_get.side_effect = None
        mock_get.return_value = _mock_response(json_data=SAMPLE_LATEST_BREACH)
        result2 = hibp_client.fetch_breach_catalog()

        assert result2 == result1  # same cached data
        assert mock_get.call_count == 1  # only latestbreach call, not full catalog

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_refetch_when_catalog_changed(self, mock_get):
        """When latest breach name changes, should refetch full catalog."""
        # First call
        mock_get.side_effect = [
            _mock_response(json_data=SAMPLE_LATEST_BREACH),
            _mock_response(json_data=SAMPLE_CATALOG),
        ]
        hibp_client.fetch_breach_catalog()

        # Second call with different latest breach
        new_latest = {**SAMPLE_LATEST_BREACH, "Name": "NewBreach2025"}
        new_catalog = SAMPLE_CATALOG + [{"Name": "NewBreach2025", "Domain": "new.com"}]
        mock_get.reset_mock()
        mock_get.side_effect = [
            _mock_response(json_data=new_latest),
            _mock_response(json_data=new_catalog),
        ]
        result = hibp_client.fetch_breach_catalog()

        assert len(result) == 3
        assert mock_get.call_count == 2  # both calls made

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_full_catalog_failure_uses_stale_cache(self, mock_get):
        """If full catalog fetch fails but we have a cache, use it."""
        # First call succeeds
        mock_get.side_effect = [
            _mock_response(json_data=SAMPLE_LATEST_BREACH),
            _mock_response(json_data=SAMPLE_CATALOG),
        ]
        hibp_client.fetch_breach_catalog()

        # Second call: latest breach changed, but full catalog fails
        new_latest = {**SAMPLE_LATEST_BREACH, "Name": "DifferentBreach"}
        mock_get.reset_mock()
        mock_get.side_effect = [
            _mock_response(json_data=new_latest),
            _mock_response(status_code=500, text="Server Error"),
        ]
        result = hibp_client.fetch_breach_catalog()

        # Should return the stale cache
        assert len(result) == 2
        assert result[0]["Name"] == "TestBreach2024"

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_complete_failure_returns_empty(self, mock_get):
        """If everything fails and no cache exists, return empty list."""
        mock_get.side_effect = httpx.ConnectTimeout("timeout")
        result = hibp_client.fetch_breach_catalog()

        assert result == []

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_non_list_response_handled(self, mock_get):
        """If /breaches returns non-list JSON, handle gracefully."""
        mock_get.side_effect = [
            _mock_response(json_data=SAMPLE_LATEST_BREACH),
            _mock_response(json_data={"error": "unexpected"}),
        ]
        result = hibp_client.fetch_breach_catalog()

        assert result == []

    @patch("app.services.monitoring.breach_sources.hibp_client.httpx.get")
    def test_user_agent_is_set(self, mock_get):
        """Verify the User-Agent header is included in requests."""
        mock_get.side_effect = [
            _mock_response(json_data=SAMPLE_LATEST_BREACH),
            _mock_response(json_data=SAMPLE_CATALOG),
        ]
        hibp_client.fetch_breach_catalog()

        # Check that headers were passed with User-Agent
        for call in mock_get.call_args_list:
            headers = call.kwargs.get("headers", {})
            assert "User-Agent" in headers
            assert "VendorSentry" in headers["User-Agent"]
