"""Scoring API endpoints"""
from datetime import datetime, timedelta
from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, VendorScore, RiskTier, StatusColor
from app.schemas import (
    VendorScoreResponse,
    VendorScoreSubscores,
    VendorScoreWeights,
    VendorScorePrevious,
    PortfolioScoreDistribution,
    PortfolioScoreTrend,
    PortfolioTrendPoint,
)
from app.services.scoring.engine import score_vendor_from_db, get_latest_score

router = APIRouter()


@router.get("/vendors/{vendor_id}/score", response_model=VendorScoreResponse)
def get_vendor_score(vendor_id: UUID, db: Session = Depends(get_db)):
    """Latest score with full breakdown - the 'why is it risky' endpoint"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    latest_score = get_latest_score(vendor_id, db)
    if not latest_score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No score found for vendor")

    # Get previous score if exists
    previous_score = None
    if latest_score.previous_score_id:
        prev = db.query(VendorScore).filter(VendorScore.id == latest_score.previous_score_id).first()
        if prev:
            previous_score = VendorScorePrevious(
                composite_score=prev.composite_score,
                tier=prev.tier,
                status_color=prev.status_color,
                computed_at=prev.computed_at
            )

    return VendorScoreResponse(
        id=latest_score.id,
        vendor_id=latest_score.vendor_id,
        computed_at=latest_score.computed_at,
        composite_score=latest_score.composite_score,
        tier=latest_score.tier,
        status_color=latest_score.status_color,
        subscores=VendorScoreSubscores(
            breach_subscore=latest_score.breach_subscore,
            access_subscore=latest_score.access_subscore,
            compliance_subscore=latest_score.compliance_subscore,
            financial_subscore=latest_score.financial_subscore
        ),
        weights=VendorScoreWeights(),
        anomaly_types=latest_score.anomaly_types,
        rationale=latest_score.rationale,
        triggered_by=latest_score.triggered_by,
        previous_score=previous_score
    )


@router.post("/vendors/{vendor_id}/rescore", response_model=VendorScoreResponse)
def rescore_vendor(vendor_id: UUID, db: Session = Depends(get_db)):
    """Force an immediate recompute"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    # Get current score as previous
    current_score = get_latest_score(vendor_id, db)
    previous_score_id = current_score.id if current_score else None

    # Generate new score
    new_score = score_vendor_from_db(
        vendor_id=str(vendor_id),
        db=db,
        triggered_by="manual",
        previous_score_id=previous_score_id
    )

    db.commit()
    db.refresh(new_score)

    return get_vendor_score(vendor_id, db)


@router.get("/portfolio/score-distribution", response_model=PortfolioScoreDistribution)
def get_portfolio_distribution(db: Session = Depends(get_db)):
    """Portfolio summary widget - Red/Yellow/Green at a glance"""
    # Get all non-archived vendors
    vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()

    by_tier: Dict[str, int] = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "CLEAR": 0
    }

    by_status_color: Dict[str, int] = {
        "RED": 0,
        "YELLOW": 0,
        "GREEN": 0
    }

    for vendor in vendors:
        latest_score = get_latest_score(vendor.id, db)
        if latest_score:
            by_tier[latest_score.tier.value] += 1
            by_status_color[latest_score.status_color.value] += 1
        else:
            by_tier["CLEAR"] += 1
            by_status_color["GREEN"] += 1

    return PortfolioScoreDistribution(
        by_tier=by_tier,
        by_status_color=by_status_color,
        total_vendors=len(vendors),
        as_of=datetime.utcnow()
    )


@router.get("/portfolio/score-trend", response_model=PortfolioScoreTrend)
def get_portfolio_trend(
    range: str = Query("90d", regex="^(30d|90d|1y)$"),
    db: Session = Depends(get_db)
):
    """Trend-over-time line chart"""
    # Parse range
    if range == "30d":
        days = 30
    elif range == "90d":
        days = 90
    else:  # 1y
        days = 365

    start_date = datetime.utcnow() - timedelta(days=days)

    # Sample daily snapshots (simplified - real implementation would snapshot actual state)
    points = []
    current_date = start_date

    while current_date <= datetime.utcnow():
        # Mock data - real implementation would query historical scores
        points.append(PortfolioTrendPoint(
            date=current_date.strftime("%Y-%m-%d"),
            by_tier={
                "CRITICAL": 10,
                "HIGH": 45,
                "MEDIUM": 100,
                "LOW": 85,
                "CLEAR": 150
            }
        ))
        current_date += timedelta(days=7)  # Weekly snapshots

    return PortfolioScoreTrend(points=points)
