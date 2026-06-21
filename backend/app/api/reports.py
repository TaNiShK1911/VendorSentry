"""Reports API endpoints"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
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


@router.get("/reports")
def list_reports(db: Session = Depends(get_db)):
    """
    List all available reports (stub - returns vendor list for frontend compatibility).
    """
    vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
    reports = []
    for vendor in vendors:
        score = db.query(VendorScore).filter(
            VendorScore.vendor_id == vendor.id
        ).order_by(VendorScore.computed_at.desc()).first()
        if score:
            reports.append({
                "vendor_id": str(vendor.id),
                "vendor_name": vendor.name,
                "report_type": "vendor_summary",
                "available_formats": ["markdown", "pdf"],
                "last_score_at": score.computed_at.isoformat() if score.computed_at else None
            })
    return {"items": reports, "total": len(reports)}


@router.post("/reports/generate")
def generate_report(
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Generate a vendor report on demand.

    Body: {"vendor_id": "<uuid>", "report_type": "vendor_summary", "format": "markdown"}
    """
    vendor_id = payload.get("vendor_id")
    report_type = payload.get("report_type", "vendor_summary")
    fmt = payload.get("format", "markdown")

    if not vendor_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="vendor_id is required")

    try:
        vendor_uuid = UUID(str(vendor_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid vendor_id UUID")

    vendor = db.query(Vendor).filter(Vendor.id == vendor_uuid).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    score = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor_uuid
    ).order_by(VendorScore.computed_at.desc()).first()

    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No score available for vendor - run scoring first")

    alerts = db.query(Alert).filter(
        Alert.vendor_id == vendor_uuid,
        Alert.resolved_at.is_(None)
    ).all()

    report = generate_vendor_report_markdown(vendor, score, alerts)

    return {
        "vendor_id": str(vendor_uuid),
        "vendor_name": vendor.name,
        "report_type": report_type,
        "format": fmt,
        "content": report,
        "generated_at": score.computed_at.isoformat() if score.computed_at else None
    }
