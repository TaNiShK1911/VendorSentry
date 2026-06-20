"""Reports API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, VendorScore, Alert
from app.services.reporting.generator import generate_vendor_report_markdown, generate_portfolio_report_markdown, markdown_to_pdf

router = APIRouter()


@router.get("/vendors/{vendor_id}/report")
def get_vendor_report(
    vendor_id: str,
    format: str = Query("markdown", pattern="^(pdf|markdown|json)$"),
    db: Session = Depends(get_db)
):
    """
    Generate audit report for a single vendor.
    Returns either application/pdf, text/markdown, or JSON.
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    score = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor_id
    ).order_by(VendorScore.computed_at.desc()).first()

    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No score available for vendor")

    alerts = db.query(Alert).filter(
        Alert.vendor_id == vendor_id,
        Alert.resolved_at.is_(None)
    ).all()

    if format == "json":
        return {
            "vendor_name": vendor.name,
            "composite_score": score.composite_score,
            "tier": score.tier,
            "status_color": score.status_color,
            "active_alerts": len(alerts),
        }

    report = generate_vendor_report_markdown(vendor, score, alerts)

    if format == "pdf":
        pdf_bytes = markdown_to_pdf(report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=vendor_{vendor.name}_report.pdf"}
        )

    return PlainTextResponse(content=report, media_type="text/markdown")


@router.get("/portfolio/report")
def get_portfolio_report(
    format: str = Query("markdown", pattern="^(pdf|markdown|json)$"),
    db: Session = Depends(get_db)
):
    """Generate full-portfolio audit report."""
    if format == "json":
        vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
        return {"total_vendors": len(vendors), "format": "json"}

    report = generate_portfolio_report_markdown(db)

    if format == "pdf":
        pdf_bytes = markdown_to_pdf(report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=portfolio_report.pdf"}
        )

    return PlainTextResponse(content=report, media_type="text/markdown")
