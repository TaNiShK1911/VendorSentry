"""Reports API endpoints"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, VendorScore, Alert
from app.services.reporting.generator import generate_vendor_report_markdown, generate_portfolio_report_markdown

router = APIRouter()


@router.get("/vendors/{vendor_id}/report")
def get_vendor_report(
    vendor_id: UUID,
    format: str = Query("markdown", regex="^(pdf|markdown)$"),
    db: Session = Depends(get_db)
):
    """
    Generate audit report for a single vendor.

    Returns either application/pdf or text/markdown.
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    # Get latest score
    score = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor_id
    ).order_by(VendorScore.computed_at.desc()).first()

    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No score available for vendor")

    # Get active alerts
    alerts = db.query(Alert).filter(
        Alert.vendor_id == vendor_id,
        Alert.resolved_at.is_(None)
    ).all()

    if format == "markdown":
        report = generate_vendor_report_markdown(vendor, score, alerts)
        return PlainTextResponse(content=report, media_type="text/markdown")
    else:
        # PDF generation would use reportlab here
        # For now, return markdown with PDF media type
        report = generate_vendor_report_markdown(vendor, score, alerts)
        return PlainTextResponse(
            content=report,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=vendor_{vendor.name}_report.pdf"}
        )


@router.get("/portfolio/report")
def get_portfolio_report(
    format: str = Query("markdown", regex="^(pdf|markdown)$"),
    db: Session = Depends(get_db)
):
    """
    Generate full-portfolio audit report.

    Risk-by-category, trending, recommendations.
    """
    if format == "markdown":
        report = generate_portfolio_report_markdown(db)
        return PlainTextResponse(content=report, media_type="text/markdown")
    else:
        # PDF generation stub
        report = generate_portfolio_report_markdown(db)
        return PlainTextResponse(
            content=report,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=portfolio_report.pdf"}
        )
