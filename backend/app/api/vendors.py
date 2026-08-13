"""Vendor CRUD API endpoints"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, VendorScore, Alert, DataAccessScope
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorListItem, VendorDetail, ImportResult, ContactInfo
from app.services.scoring.engine import score_vendor, get_latest_score
from app.services.extraction.narrative import generate_rationale

router = APIRouter()


@router.get("/vendors")
def list_vendors(
    q: Optional[str] = None,
    search: Optional[str] = None,
    tier: Optional[str] = None,
    type: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    has_pii_access: Optional[bool] = None,
    has_pii: Optional[bool] = None,
    cert_expiring_within_days: Optional[int] = None,
    sort: str = "score_desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    per_page: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List/search/filter vendors - backs the main portfolio grid"""
    # Accept both 'q' and 'search' param names
    search_term = q or search
    # Accept both 'page_size' and 'per_page'
    actual_page_size = per_page or page_size
    # Accept both 'has_pii_access' and 'has_pii'
    pii_filter = has_pii_access if has_pii_access is not None else has_pii

    from sqlalchemy import func as sa_func

    # Subquery to get only the latest vendor record for each unique vendor name
    latest_vendor_subq = (
        db.query(
            Vendor.id,
            sa_func.row_number().over(
                partition_by=Vendor.name,
                order_by=Vendor.last_assessed_at.desc().nulls_last()
            ).label('rn')
        )
        .filter(Vendor.archived_at.is_(None))
        .subquery()
    )

    query = (
        db.query(Vendor)
        .join(latest_vendor_subq, Vendor.id == latest_vendor_subq.c.id)
        .filter(latest_vendor_subq.c.rn == 1)
    )

    # Apply filters
    if search_term:
        query = query.filter(Vendor.name.ilike(f"%{search_term}%"))

    if type:
        query = query.filter(Vendor.vendor_type == type)

    # Get total count
    total_items = query.count()

    # Pagination
    offset = (page - 1) * actual_page_size
    vendors = query.offset(offset).limit(actual_page_size).all()
    
    vendor_ids = [v.id for v in vendors]
    vendor_names = [v.name for v in vendors]
    
    # Find ALL vendor_ids that share these names (including historical duplicates)
    all_vendor_ids_query = db.query(Vendor.id).filter(Vendor.name.in_(vendor_names)).all()
    all_vendor_ids = [v.id for v in all_vendor_ids_query]
    
    # Batch fetch latest scores for these vendors (grouped by name)
    from sqlalchemy import func
    from sqlalchemy.orm import aliased
    
    subq = db.query(
        VendorScore.id,
        sa_func.row_number().over(
            partition_by=Vendor.name,
            order_by=VendorScore.computed_at.desc()
        ).label("rn")
    ).join(Vendor, Vendor.id == VendorScore.vendor_id).filter(Vendor.name.in_(vendor_names)).subquery()
    
    latest_scores = (
        db.query(VendorScore, Vendor.name)
        .join(subq, VendorScore.id == subq.c.id)
        .filter(subq.c.rn == 1)
        .join(Vendor, Vendor.id == VendorScore.vendor_id)
        .all()
    )
    score_map = {name: score for score, name in latest_scores}
    
    # Batch fetch alert counts across all vendor IDs for each name
    alert_counts = db.query(
        Vendor.name,
        func.count(Alert.id).label("count")
    ).join(Alert, Alert.vendor_id == Vendor.id).filter(
        Vendor.name.in_(vendor_names),
        Alert.resolved_at.is_(None)
    ).group_by(Vendor.name).all()
    alert_count_map = {name: count for name, count in alert_counts}
    
    # Batch fetch scopes
    scopes = db.query(DataAccessScope).filter(DataAccessScope.vendor_id.in_(vendor_ids)).all()
    scope_map = {s.vendor_id: s for s in scopes}

    # Build response items in the format frontend expects
    items = []
    for vendor in vendors:
        # Get latest score
        latest_score = score_map.get(vendor.name)

        # Count active alerts
        alert_count = alert_count_map.get(vendor.name, 0)

        # Check PII access from DataAccessScope relationship
        has_pii_val = False
        scope = scope_map.get(vendor.id)
        if scope:
            has_pii_val = scope.pii_access

        # Map to frontend's expected field names
        items.append({
            "id": vendor.id,
            "name": vendor.name,
            "vendor_type": vendor.vendor_type,
            "contact_email": vendor.contact_email or "",
            "website_domain": vendor.website_domain,
            "annual_spend": float(vendor.annual_spend) if vendor.annual_spend else 0,
            "contract_start": str(vendor.contract_start) if vendor.contract_start else None,
            "contract_end": str(vendor.contract_end) if vendor.contract_end else None,
            "has_pii_access": has_pii_val,
            "has_financial_access": scope.financial_access if scope else False,
            "systems_access": scope.systems if scope else [],
            "data_access_notes": scope.scope_notes if scope else "",
            "status": vendor.contract_status or "active",
            "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
            "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
            "composite_score": latest_score.composite_score if latest_score else 0.0,
            "status_color": latest_score.status_color if latest_score else "GREEN",
            "risk_tier": latest_score.tier if latest_score else "CLEAR",
            "active_alerts": alert_count,
            "last_assessed": vendor.last_assessed_at.isoformat() if vendor.last_assessed_at else None,
        })

    total_pages = (total_items + actual_page_size - 1) // actual_page_size

    # Return in the format the frontend expects
    return {
        "vendors": items,
        "pagination": {
            "page": page,
            "per_page": actual_page_size,
            "total": total_items,
            "total_pages": total_pages,
        }
    }


@router.post("/vendors/import")
async def import_vendors(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Multipart CSV upload (vendor_registry.csv shape)"""
    from app.services.ingestion.csv_importer import import_csv_file

    content = await file.read()
    result = import_csv_file(content, db, triggered_by="csv_import")
    db.commit()

    return ImportResult(
        rows_processed=result["rows_processed"],
        rows_succeeded=result["rows_succeeded"],
        rows_failed=result["rows_failed"],
        errors=result["errors"],
    )


@router.get("/vendors/export.csv")
def export_vendors(db: Session = Depends(get_db)):
    """Export vendors as CSV for audit purposes."""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from sqlalchemy import func

    vendors = db.query(Vendor).filter(Vendor.archived_at.is_(None)).all()
    vendor_ids = [v.id for v in vendors]

    subq = db.query(
        VendorScore.vendor_id,
        func.max(VendorScore.computed_at).label("max_computed_at")
    ).filter(VendorScore.vendor_id.in_(vendor_ids)).group_by(VendorScore.vendor_id).subquery()

    latest_scores = db.query(VendorScore).join(
        subq,
        (VendorScore.vendor_id == subq.c.vendor_id) &
        (VendorScore.computed_at == subq.c.max_computed_at)
    ).all()
    score_map = {s.vendor_id: s for s in latest_scores}

    from app.models.certification import Certification
    all_certs = db.query(Certification).filter(Certification.vendor_id.in_(vendor_ids)).all()
    cert_map: dict[str, list] = {}
    for c in all_certs:
        cert_map.setdefault(c.vendor_id, []).append(c)

    scopes = db.query(DataAccessScope).filter(DataAccessScope.vendor_id.in_(vendor_ids)).all()
    scope_map = {s.vendor_id: s for s in scopes}

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "vendor_id", "vendor_name", "vendor_type",
            "composite_score", "tier", "status_color",
            "anomaly_types", "breach_status",
            "certifications", "contract_end_date", "last_audit_date",
            "data_access_scope", "financial_health", "risk_score",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for vendor in vendors:
            score = score_map.get(vendor.id)
            scope = scope_map.get(vendor.id)
            certs = cert_map.get(vendor.id, [])

            cert_strs = []
            for c in certs:
                if c.expiry_date:
                    cert_strs.append(f"{c.cert_type}:{c.expiry_date.isoformat()}")
                else:
                    cert_strs.append(c.cert_type)
            cert_str = "|".join(cert_strs)

            anomaly_types = score.anomaly_types if score else []
            if "BREACHED_VENDOR_HIGH_ACCESS" in anomaly_types:
                breach_status = "Recent_Breach_12mo"
            elif "RECENTLY_BREACHED_VENDOR" in anomaly_types:
                breach_status = "Recent_Breach_12mo"
            elif vendor.under_investigation:
                breach_status = "Under_Investigation"
            else:
                breach_status = "No_Known_Breach"

            if scope and scope.broad_system_access:
                access_label = "All_Systems"
            elif scope and scope.pii_access:
                access_label = "Customer_PII"
            elif scope and scope.financial_access:
                access_label = "Financial_Data"
            else:
                access_label = "Internal_Data"

            writer.writerow([
                vendor.source_vendor_id or vendor.id,
                vendor.name,
                vendor.vendor_type,
                score.composite_score if score else "",
                score.tier if score else "",
                score.status_color if score else "",
                "|".join(anomaly_types),
                breach_status,
                cert_str,
                vendor.contract_end.isoformat() if vendor.contract_end else "",
                vendor.last_assessed_at.date().isoformat() if vendor.last_assessed_at else "",
                access_label,
                vendor.financial_health_signal,
                vendor.source_risk_score if vendor.source_risk_score else "",
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vendor_export.csv"},
    )


@router.get("/vendors/{vendor_id}")
def get_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Get full vendor profile - drill-down view"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found"
        )

    # Get latest score across all vendors with the same name
    latest_score = (
        db.query(VendorScore)
        .join(Vendor, Vendor.id == VendorScore.vendor_id)
        .filter(Vendor.name == vendor.name)
        .order_by(VendorScore.computed_at.desc())
        .first()
    )

    # Get score history (last 10) across all vendors with the same name
    score_history = (
        db.query(VendorScore)
        .join(Vendor, Vendor.id == VendorScore.vendor_id)
        .filter(Vendor.name == vendor.name)
        .order_by(VendorScore.computed_at.desc())
        .limit(10)
        .all()
    )

    # Get data access scope
    scope = db.query(DataAccessScope).filter(
        DataAccessScope.vendor_id == vendor.id
    ).first()

    # Get alerts count across all vendors with the same name
    alert_count = (
        db.query(Alert)
        .join(Vendor, Vendor.id == Alert.vendor_id)
        .filter(Vendor.name == vendor.name, Alert.resolved_at.is_(None))
        .count()
    )

    return {
        "id": vendor.id,
        "name": vendor.name,
        "vendor_type": vendor.vendor_type,
        "contact_email": vendor.contact_email or "",
        "website_domain": vendor.website_domain,
        "annual_spend": float(vendor.annual_spend) if vendor.annual_spend else 0,
        "contract_start": str(vendor.contract_start) if vendor.contract_start else None,
        "contract_end": str(vendor.contract_end) if vendor.contract_end else None,
        "has_pii_access": scope.pii_access if scope else False,
        "has_financial_access": scope.financial_access if scope else False,
        "systems_access": scope.systems if scope else [],
        "data_access_notes": scope.scope_notes if scope else "",
        "status": vendor.contract_status or "active",
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
        "composite_score": latest_score.composite_score if latest_score else 0.0,
        "status_color": latest_score.status_color if latest_score else "GREEN",
        "risk_tier": latest_score.tier if latest_score else "CLEAR",
        "active_alerts": alert_count,
        "last_assessed": vendor.last_assessed_at.isoformat() if vendor.last_assessed_at else None,
        "contract_days_remaining": (vendor.contract_end - vendor.contract_end.__class__.today()).days if vendor.contract_end else None,
        "current_score": {
            "composite_score": latest_score.composite_score,
            "tier": latest_score.tier,
            "status_color": latest_score.status_color,
            "subscores": {
                "breach_subscore": latest_score.breach_subscore,
                "access_subscore": latest_score.access_subscore,
                "compliance_subscore": latest_score.compliance_subscore,
                "financial_subscore": latest_score.financial_subscore,
            },
            "anomaly_types": latest_score.anomaly_types or [],
            "rationale": latest_score.rationale,
            "triggered_by": latest_score.triggered_by,
            "computed_at": latest_score.computed_at.isoformat() if latest_score.computed_at else None,
        } if latest_score else None,
        "score_history": [
            {
                "composite_score": s.composite_score,
                "tier": s.tier,
                "status_color": s.status_color,
                "computed_at": s.computed_at.isoformat() if s.computed_at else None,
            }
            for s in score_history
        ],
        # Legacy fields for backward compat with other schemas
        "contact": vendor.contact,
        "certifications": [],
        "data_access_scope": {
            "pii_access": scope.pii_access,
            "financial_access": scope.financial_access,
            "broad_system_access": scope.broad_system_access,
            "systems": scope.systems,
            "scope_notes": scope.scope_notes,
        } if scope else None,
        "breach_history": [],
        "financial_health_signal": vendor.financial_health_signal,
        "financial_health_source": vendor.financial_health_source,
        "under_investigation": vendor.under_investigation,
    }


@router.post("/vendors", status_code=status.HTTP_201_CREATED)
def create_vendor(vendor_data: VendorCreate, db: Session = Depends(get_db)):
    """Create a vendor manually"""
    vendor = Vendor(
        name=vendor_data.name,
        vendor_type=vendor_data.vendor_type,
        contact=vendor_data.contact.model_dump() if vendor_data.contact else None,
        website_domain=vendor_data.website_domain,
        annual_spend=vendor_data.annual_spend,
        contract_start=vendor_data.contract_start,
        contract_end=vendor_data.contract_end,
        contract_status=vendor_data.contract_status,
        financial_health_signal=vendor_data.financial_health_signal,
        financial_health_source=vendor_data.financial_health_source,
        under_investigation=vendor_data.under_investigation,
    )
    db.add(vendor)
    db.flush()

    # Create DataAccessScope from frontend form fields
    scope = DataAccessScope(
        vendor_id=vendor.id,
        pii_access=vendor_data.has_pii_access or False,
        financial_access=vendor_data.has_financial_access or False,
        broad_system_access=False,  # default unless updated via extraction
        systems=vendor_data.systems_access or [],
        scope_notes=vendor_data.data_access_notes,
    )
    db.add(scope)
    db.flush()

    # Trigger initial scoring
    breaches = vendor.breach_history
    certs = vendor.certifications
    result = score_vendor(vendor, breaches, certs, scope, triggered_by="manual")

    rationale = generate_rationale(
        vendor_name=vendor.name,
        composite_score=result.composite_score,
        tier=result.tier,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        anomaly_types=result.anomaly_types,
    )

    score_row = VendorScore(
        vendor_id=vendor.id,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        composite_score=result.composite_score,
        tier=result.tier,
        status_color=result.status_color,
        anomaly_types=result.anomaly_types,
        triggered_by=result.triggered_by,
        rationale=rationale,
    )
    db.add(score_row)
    db.commit()

    return get_vendor(vendor.id, db)


@router.patch("/vendors/{vendor_id}")
def update_vendor(vendor_id: str, vendor_data: VendorUpdate, db: Session = Depends(get_db)):
    """Partial update - triggers async rescore"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    # Update fields
    update_data = vendor_data.model_dump(exclude_unset=True)
    scope_fields = {"has_pii_access", "has_financial_access", "systems_access", "data_access_notes"}
    
    for field, value in update_data.items():
        if field in scope_fields:
            continue
        if field == "contact" and value is not None:
            setattr(vendor, field, value if isinstance(value, dict) else value.model_dump())
        else:
            setattr(vendor, field, value)

    # Update or create DataAccessScope
    scope = db.query(DataAccessScope).filter(DataAccessScope.vendor_id == vendor.id).first()
    if not scope:
        scope = DataAccessScope(vendor_id=vendor.id)
        db.add(scope)

    if "has_pii_access" in update_data:
        scope.pii_access = update_data["has_pii_access"] or False
    if "has_financial_access" in update_data:
        scope.financial_access = update_data["has_financial_access"] or False
    if "systems_access" in update_data:
        scope.systems = update_data["systems_access"] or []
    if "data_access_notes" in update_data:
        scope.scope_notes = update_data["data_access_notes"]

    db.flush()

    # Trigger rescore
    breaches = vendor.breach_history
    certs = vendor.certifications
    result = score_vendor(vendor, breaches, certs, scope, triggered_by="manual")

    rationale = generate_rationale(
        vendor_name=vendor.name,
        composite_score=result.composite_score,
        tier=result.tier,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        anomaly_types=result.anomaly_types,
    )

    score_row = VendorScore(
        vendor_id=vendor.id,
        breach_subscore=result.breach_subscore,
        access_subscore=result.access_subscore,
        compliance_subscore=result.compliance_subscore,
        financial_subscore=result.financial_subscore,
        composite_score=result.composite_score,
        tier=result.tier,
        status_color=result.status_color,
        anomaly_types=result.anomaly_types,
        triggered_by=result.triggered_by,
        rationale=rationale,
    )
    db.add(score_row)
    db.commit()

    return get_vendor(vendor.id, db)


@router.delete("/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Soft-delete (sets archived_at)"""
    from datetime import datetime

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    vendor.archived_at = datetime.utcnow()
    return None

@router.post("/vendors/{vendor_id}/onboarding-checklist")
def generate_onboarding(vendor_id: str, db: Session = Depends(get_db)):
    """Generate dynamic onboarding checklist using LLM."""
    from app.models.vendor_task import VendorTask
    from app.services.generation.onboarding import generate_onboarding_tasks

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    latest_score = db.query(VendorScore).filter(VendorScore.vendor_id == vendor_id).order_by(VendorScore.computed_at.desc()).first()

    # Generate tasks
    tasks = generate_onboarding_tasks(vendor, latest_score)

    # Save to DB
    created_tasks = []
    for t in tasks:
        vt = VendorTask(
            vendor_id=vendor_id,
            title=t.get("title", "Untitled Task"),
            description=t.get("description", ""),
            task_type="onboarding"
        )
        db.add(vt)
        created_tasks.append(vt)

    db.commit()
    
    return [
        {
            "id": vt.id,
            "title": vt.title,
            "description": vt.description,
            "is_completed": vt.is_completed,
            "task_type": vt.task_type,
            "created_at": vt.created_at.isoformat() if vt.created_at else None
        } for vt in created_tasks
    ]

@router.get("/vendors/{vendor_id}/remediation-history")
def get_remediation_history(vendor_id: str, db: Session = Depends(get_db)):
    """Get all tasks (onboarding/remediation) for a vendor."""
    from app.models.vendor_task import VendorTask
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    tasks = db.query(VendorTask).filter(VendorTask.vendor_id == vendor_id).order_by(VendorTask.created_at.asc()).all()
    
    return [
        {
            "id": vt.id,
            "title": vt.title,
            "description": vt.description,
            "is_completed": vt.is_completed,
            "task_type": vt.task_type,
            "created_at": vt.created_at.isoformat() if vt.created_at else None,
            "updated_at": vt.updated_at.isoformat() if vt.updated_at else None
        } for vt in tasks
    ]

@router.patch("/vendors/{vendor_id}/tasks/{task_id}")
def update_task_status(vendor_id: str, task_id: str, payload: dict, db: Session = Depends(get_db)):
    """Update a task (e.g., mark complete)."""
    from app.models.vendor_task import VendorTask
    
    task = db.query(VendorTask).filter(VendorTask.vendor_id == vendor_id, VendorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if "is_completed" in payload:
        task.is_completed = payload["is_completed"]

    db.commit()
    
    return {
        "id": task.id,
        "title": task.title,
        "is_completed": task.is_completed
    }
