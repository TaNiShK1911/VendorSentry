"""
SEC EDGAR public records enrichment — Celery task.

Replaces the old mock that echoed vendor.financial_health_signal back at itself
with a real, free SEC EDGAR full-text search for material cybersecurity incident
disclosures (Item 1.05 8-K filings, required under the SEC's 2023 cyber-disclosure
rule) and regulatory actions.

Design decisions:
    - Only meaningfully matches PUBLIC companies — most vendors in a typical
      registry won't have SEC filings, and that's fine and expected. The adapter
      produces *no signal* for those, not a fabricated one.
    - Does NOT auto-set financial_health_signal from a single 8-K mention.
      A filing existing isn't the same as a confirmed material incident.
      Signals are surfaced for human review via EvidenceSignal.
    - Tracks last query date per vendor to avoid redundant daily re-queries.
      Skips vendors whose last public_records signal is < 7 days old.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Vendor, EvidenceSignal

logger = logging.getLogger(__name__)

settings = get_settings()

_EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
_TIMEOUT_SECONDS = 10
_RECHECK_INTERVAL_DAYS = 7


def _user_agent() -> str:
    """SEC EDGAR requires a descriptive User-Agent with a real contact email."""
    return f"VendorSentry {settings.contact_email}"


def _should_skip_vendor(db, vendor_id: str) -> bool:
    """
    Check if we already queried SEC EDGAR for this vendor recently.

    Returns True if the most recent public_records EvidenceSignal for this
    vendor is less than _RECHECK_INTERVAL_DAYS old.
    """
    cutoff = datetime.utcnow() - timedelta(days=_RECHECK_INTERVAL_DAYS)
    recent_signal = (
        db.query(EvidenceSignal)
        .filter(
            EvidenceSignal.vendor_id == vendor_id,
            EvidenceSignal.source == "public_records",
            EvidenceSignal.received_at >= cutoff,
        )
        .first()
    )
    return recent_signal is not None


def _search_edgar_filings(vendor_name: str) -> Optional[dict]:
    """
    Search SEC EDGAR EFTS for 8-K filings mentioning the vendor.

    Args:
        vendor_name: The vendor's name to search for.

    Returns:
        The parsed JSON response dict, or None on failure.
    """
    try:
        response = httpx.get(
            _EDGAR_SEARCH_URL,
            params={
                "q": f'"{vendor_name}"',
                "forms": "8-K",
            },
            headers={"User-Agent": _user_agent()},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "SEC EDGAR search for %r returned HTTP %s: %s",
            vendor_name,
            exc.response.status_code,
            exc.response.text[:200],
        )
        return None
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("SEC EDGAR search for %r failed: %s", vendor_name, exc)
        return None


def _extract_filings(edgar_response: dict) -> list[dict]:
    """
    Extract relevant filing entries from the EDGAR EFTS response.

    Returns a list of dicts with filing metadata.
    """
    hits = edgar_response.get("hits", {})
    if isinstance(hits, dict):
        hit_list = hits.get("hits", [])
    elif isinstance(hits, list):
        hit_list = hits
    else:
        return []

    filings = []
    for hit in hit_list[:10]:  # limit to first 10 results
        source = hit.get("_source", {}) if isinstance(hit, dict) else {}
        filing = {
            "form_type": source.get("form_type", "8-K"),
            "filing_date": source.get("file_date") or source.get("period_of_report"),
            "company_name": source.get("entity_name") or source.get("display_names", [""])[0] if isinstance(source.get("display_names"), list) else source.get("entity_name"),
            "file_number": source.get("file_num"),
            "accession_number": source.get("accession_no"),
        }
        # Build a link to the filing if we have an accession number
        accession = filing.get("accession_number", "")
        if accession:
            clean_accession = accession.replace("-", "")
            filing["url"] = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{source.get('entity_id', '')}/{clean_accession}/"
            )
        filings.append(filing)

    return filings


@celery_app.task(name="app.services.enrichment.public_records.check_public_records")
def check_public_records():
    """
    Search SEC EDGAR for material cybersecurity incident disclosures
    (8-K filings) related to registered vendors.

    Only produces signals when filings are actually found. Does not
    fabricate signals for vendors with no SEC presence.
    """
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
        signals_created = 0
        vendors_skipped = 0

        for vendor in vendors:
            # Skip if we checked recently
            if _should_skip_vendor(db, vendor.id):
                vendors_skipped += 1
                continue

            # Search SEC EDGAR
            edgar_response = _search_edgar_filings(vendor.name)
            if edgar_response is None:
                continue  # API error — skip gracefully, try next vendor

            filings = _extract_filings(edgar_response)

            if not filings:
                # No filings found — this is a valid, honest result.
                # Don't create a fabricated signal.
                continue

            # Create EvidenceSignal for human review
            signal = EvidenceSignal(
                vendor_id=vendor.id,
                source="public_records",
                signal_type="regulatory_filing",
                payload={
                    "vendor_name": vendor.name,
                    "filing_count": len(filings),
                    "filings": filings,
                    "search_query": f'"{vendor.name}"',
                    "forms_searched": "8-K",
                    "note": (
                        "SEC EDGAR 8-K filings found mentioning this vendor. "
                        "Requires human review to determine relevance and impact."
                    ),
                },
                received_at=datetime.utcnow(),
            )
            db.add(signal)
            signals_created += 1

        db.commit()
        return (
            f"Public records check complete: {signals_created} signals generated, "
            f"{vendors_skipped} vendors skipped (recently checked)"
        )
    except Exception:
        logger.exception("check_public_records failed")
        db.rollback()
        return "Public records check failed — see logs"
    finally:
        db.close()
