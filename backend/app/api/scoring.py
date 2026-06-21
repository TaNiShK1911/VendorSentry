"""Scoring API endpoints"""
from datetime import datetime, timedelta
from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, VendorScore
from app.services.scoring.engine import score_vendor, get_latest_score

router = APIRouter()


@router.get("/vendors/{vendor_id}/score")
def get_vendor_score(vendor_id: str, db: Session = Depends(get_db)):
    """Latest score with full breakdown"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    latest_score = get_latest_score(vendor_id, db)
    if not latest_score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No score found for vendor")

    # Get previous score if exists
    previous_score_val = 0.0
    if latest_score.previous_score_id:
        prev = db.query(VendorScore).filter(VendorScore.id == latest_score.previous_score_id).first()
        if prev:
            previous_score_val = prev.composite_score

    # Get score history
    score_history = db.query(VendorScore).filter(
        VendorScore.vendor_id == vendor_id
    ).order_by(VendorScore.computed_at.desc()).limit(10).all()

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        "composite_score": latest_score.composite_score,
        "status_color": latest_score.status_color,
        "risk_tier": latest_score.tier,
        "previous_score": previous_score_val,
        "score_delta": round(latest_score.composite_score - previous_score_val, 2),
        "assessed_at": latest_score.computed_at.isoformat() if latest_score.computed_at else None,
        "subscores": {
            "breach_risk": {
                "score": latest_score.breach_subscore,
                "weight": 0.40,
                "weighted_score": round(latest_score.breach_subscore * 0.40, 2),
                "factors": [],
            },
            "access_risk": {
                "score": latest_score.access_subscore,
                "weight": 0.25,
                "weighted_score": round(latest_score.access_subscore * 0.25, 2),
                "factors": [],
            },
            "compliance_risk": {
                "score": latest_score.compliance_subscore,
                "weight": 0.20,
                "weighted_score": round(latest_score.compliance_subscore * 0.20, 2),
                "factors": [],
            },
            "financial_risk": {
                "score": latest_score.financial_subscore,
                "weight": 0.15,
                "weighted_score": round(latest_score.financial_subscore * 0.15, 2),
                "factors": [],
            },
        },
        "anomaly_types": latest_score.anomaly_types or [],
        "trigger_sources": [latest_score.triggered_by],
        "rationale": latest_score.rationale or "Score computed by deterministic scoring engine.",
        "score_history": [
            {
                "date": s.computed_at.isoformat() if s.computed_at else None,
                "score": s.composite_score,
                "tier": s.tier,
                "reason": s.triggered_by,
            }
            for s in score_history
        ],
    }


@router.post("/vendors/{vendor_id}/rescore")
def rescore_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Force an immediate recompute"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    # Run scoring
    breaches = vendor.breach_history
    certs = vendor.certifications
    scope = vendor.data_access_scope
    result = score_vendor(vendor, breaches, certs, scope, triggered_by="manual")

    # Get current score as previous
    current_score = get_latest_score(vendor_id, db)
    previous_score_id = current_score.id if current_score else None

    score_row = VendorScore(
        vendor_id=vendor_id,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        composite_score=result.composite_score,
        tier=result.tier,
        status_color=result.status_color,
        anomaly_types=result.anomaly_types,
        triggered_by=result.triggered_by,
        previous_score_id=previous_score_id,
    )
    db.add(score_row)
    db.commit()

    return get_vendor_score(vendor_id, db)


@router.get("/portfolio/score-distribution")
def get_portfolio_distribution(db: Session = Depends(get_db)):
    """Portfolio summary widget - Red/Yellow/Green at a glance"""
    vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()

    by_tier = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "CLEAR": 0}
    by_status_color = {"RED": 0, "YELLOW": 0, "GREEN": 0}
    scores = []

    for vendor in vendors:
        latest_score = get_latest_score(vendor.id, db)
        if latest_score:
            tier_val = latest_score.tier if isinstance(latest_score.tier, str) else latest_score.tier.value
            color_val = latest_score.status_color if isinstance(latest_score.status_color, str) else latest_score.status_color.value
            by_tier[tier_val] = by_tier.get(tier_val, 0) + 1
            by_status_color[color_val] = by_status_color.get(color_val, 0) + 1
            scores.append(latest_score.composite_score)
        else:
            by_tier["CLEAR"] += 1
            by_status_color["GREEN"] += 1
            scores.append(0.0)

    avg_score = sum(scores) / len(scores) if scores else 0.0
    sorted_scores = sorted(scores)
    median_score = sorted_scores[len(sorted_scores) // 2] if sorted_scores else 0.0

    return {
        "by_tier": by_tier,
        "by_status_color": by_status_color,
        "total_vendors": len(vendors),
        "avg_composite_score": round(avg_score, 2),
        "median_score": round(median_score, 2),
        "highest_score": max(scores) if scores else 0.0,
        "lowest_score": min(scores) if scores else 0.0,
    }


@router.get("/portfolio/score-trend")
def get_portfolio_trend(
    range: str = Query("90d", pattern="^(30d|90d|1y)$"),
    db: Session = Depends(get_db)
):
    """Trend-over-time line chart"""
    if range == "30d":
        days = 30
        step_days = 1
    elif range == "90d":
        days = 90
        step_days = 7
    else:
        days = 365
        step_days = 30

    points = []
    total_vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).count()
    
    max_date = db.query(sa_func.max(VendorScore.computed_at)).scalar()
    if not max_date:
        max_date = datetime.utcnow()
        
    start_date = max_date - timedelta(days=days)
    current_date = start_date

    while current_date <= max_date:
        # Get latest score for each vendor as of current_date
        subquery = (
            db.query(
                VendorScore.vendor_id,
                sa_func.max(VendorScore.computed_at).label('max_date')
            )
            .filter(VendorScore.computed_at <= current_date)
            .group_by(VendorScore.vendor_id)
            .subquery()
        )
        
        scores_at_date = (
            db.query(VendorScore)
            .join(subquery, 
                  (VendorScore.vendor_id == subquery.c.vendor_id) & 
                  (VendorScore.computed_at == subquery.c.max_date))
            .all()
        )
        
        if scores_at_date:
            avg_score = sum(s.composite_score for s in scores_at_date) / len(scores_at_date)
            risk_count = sum(1 for s in scores_at_date if s.tier in ["CRITICAL", "HIGH"])
            
            points.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "avg_score": round(avg_score, 2),
                "risk_vendor_count": risk_count,
                "total_vendors": total_vendors,
            })
            
        current_date += timedelta(days=step_days)

    return {
        "range": range,
        "data_points": points,
    }


@router.get("/vendors/{vendor_id}/certifications")
def get_vendor_certifications(vendor_id: str, db: Session = Depends(get_db)):
    from app.models import Certification
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
        
    certs = db.query(Certification).filter(Certification.vendor_id == vendor_id).all()
    return {
        "vendor_id": vendor_id,
        "certifications": [
            {
                "id": c.id,
                "name": c.cert_type,
                "status": c.status,
                "issue_date": c.issued_date.isoformat() if c.issued_date else "",
                "expiry_date": c.expiry_date.isoformat() if c.expiry_date else "",
                "source": c.source,
                "days_until_expiry": (c.expiry_date - datetime.utcnow().date()).days if c.expiry_date else 0
            } for c in certs
        ]
    }


@router.get("/vendors/{vendor_id}/breaches")
def get_vendor_breaches(vendor_id: str, db: Session = Depends(get_db)):
    from app.models import BreachEvent
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
        
    breaches = db.query(BreachEvent).filter(BreachEvent.vendor_id == vendor_id).order_by(BreachEvent.breach_date.desc()).all()
    return {
        "vendor_id": vendor_id,
        "breaches": [
            {
                "id": b.id,
                "date": b.breach_date.isoformat() if b.breach_date else "",
                "source": b.source,
                "description": b.description,
                "severity": b.severity,
                "records_affected": getattr(b, 'records_affected', 0)
            } for b in breaches
        ]
    }
