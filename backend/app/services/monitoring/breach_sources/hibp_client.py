"""
HIBP (Have I Been Pwned) client — polls the free, unauthenticated breach catalog.

Caching strategy (per HIBP's own guidance):
    1. Call /api/v3/latestbreach (cheap, heavily-cached) to check if the catalog changed.
    2. Only call /api/v3/breaches (the full ~900+ record list) when the latest breach
       name differs from the cached value.
    3. Never poll the full catalog on every Celery beat tick.

Both endpoints are free and require no API key, but they DO require a descriptive
User-Agent header — HIBP returns 403 without one.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_HIBP_BASE_URL = "https://haveibeenpwned.com/api/v3"
_TIMEOUT_SECONDS = 10

# Module-level cache — survives across Celery task invocations within the same worker
_cached_catalog: list[dict] = []
_cached_latest_name: Optional[str] = None


def _user_agent() -> str:
    return f"VendorSentry-BreachWatcher (contact: {settings.contact_email})"


def fetch_latest_breach() -> Optional[dict]:
    """
    GET /api/v3/latestbreach — returns the single most recent breach entry.

    This is a cheap, heavily-cached endpoint intended to be polled frequently
    to detect *whether* the catalog changed at all.

    Returns:
        The latest breach dict, or None on failure.
    """
    try:
        response = httpx.get(
            f"{_HIBP_BASE_URL}/latestbreach",
            headers={"User-Agent": _user_agent()},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HIBP /latestbreach returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return None
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("HIBP /latestbreach failed: %s", exc)
        return None


def _fetch_full_catalog() -> list[dict]:
    """
    GET /api/v3/breaches — returns the full breach catalog (~900+ entries).

    Should only be called when fetch_latest_breach() indicates a change.
    """
    try:
        response = httpx.get(
            f"{_HIBP_BASE_URL}/breaches",
            headers={"User-Agent": _user_agent()},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            logger.warning("HIBP /breaches returned non-list: %s", type(data))
            return []
        return data
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HIBP /breaches returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return []
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("HIBP /breaches failed: %s", exc)
        return []


def fetch_breach_catalog() -> list[dict]:
    """
    Return the HIBP breach catalog, using conditional fetch to avoid
    hammering the full /breaches endpoint on every poll.

    Strategy:
        1. Check /latestbreach for the name of the most recent breach.
        2. If it matches the cached value, return the cached catalog.
        3. If it differs (or no cache exists), fetch the full catalog.
    """
    global _cached_catalog, _cached_latest_name

    latest = fetch_latest_breach()
    latest_name = latest.get("Name") if latest else None

    # If the latest breach name hasn't changed and we have a cache, reuse it
    if latest_name and latest_name == _cached_latest_name and _cached_catalog:
        logger.debug(
            "HIBP catalog unchanged (latest=%s), using cache (%d entries)",
            latest_name,
            len(_cached_catalog),
        )
        return _cached_catalog

    # Catalog changed or no cache — fetch the full list
    logger.info(
        "HIBP catalog changed (cached=%s, latest=%s) — fetching full catalog",
        _cached_latest_name,
        latest_name,
    )
    new_catalog = _fetch_full_catalog()

    if new_catalog:
        _cached_catalog = new_catalog
        _cached_latest_name = latest_name
    elif _cached_catalog:
        # Full fetch failed but we have a stale cache — use it
        logger.warning(
            "HIBP full catalog fetch failed, using stale cache (%d entries)",
            len(_cached_catalog),
        )
    else:
        logger.warning("HIBP: no catalog available (first fetch failed)")

    return _cached_catalog
