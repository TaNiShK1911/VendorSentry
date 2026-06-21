"""Extraction and evidence API endpoints"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, ExtractionJob, EvidenceSignal, ExtractionStatus, DocumentType
from app.schemas import ExtractionJobCreate, ExtractionJobResponse, EvidenceSignalResponse
from app.services.extraction.extractor import extract_from_text

router = APIRouter()


@router.get("/extraction-jobs", response_model=dict)
def list_extraction_jobs(
    vendor_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all extraction jobs, optionally filtered by vendor."""
    query = db.query(ExtractionJob)
    if vendor_id:
        query = query.filter(ExtractionJob.vendor_id == vendor_id)

    total_items = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(ExtractionJob.created_at.desc()).offset(offset).limit(page_size).all()

    items = [
        ExtractionJobResponse(
            id=job.id,
            vendor_id=job.vendor_id,
            document_type=job.document_type,
            status=job.status.value if hasattr(job.status, "value") else job.status,
            structured_output=job.structured_output,
            conflicts=job.conflicts or [],
            completed_at=job.completed_at
        )
        for job in jobs
    ]

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": (total_items + page_size - 1) // page_size if total_items > 0 else 1
    }


@router.post("/vendors/{vendor_id}/extract", response_model=ExtractionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def extract_document(
    vendor_id: UUID,
    document_type: DocumentType = Form(...),
    text: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    Multipart upload (PDF or pasted text) - kicks off async extraction job.

    Accepts either text field or file upload.
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    # Get text content
    if file:
        content = await file.read()
        raw_text = content.decode('utf-8', errors='ignore')
    elif text:
        raw_text = text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text or file must be provided"
        )

    # Create extraction job
    job = ExtractionJob(
        vendor_id=vendor_id,
        document_type=document_type,
        raw_text=raw_text,
        status=ExtractionStatus.PENDING,
        created_at=datetime.utcnow()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Process synchronously using the stub
    try:
        job.status = ExtractionStatus.PROCESSING
        db.commit()

        # Call extraction service (stub for now)
        structured_output = extract_from_text(vendor_id, document_type.value, raw_text)

        job.status = ExtractionStatus.DONE
        job.structured_output = structured_output
        job.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(job)

    except Exception as e:
        job.status = ExtractionStatus.FAILED
        job.error_message = str(e)
        db.commit()

    return ExtractionJobResponse(
        id=job.id,
        vendor_id=job.vendor_id,
        document_type=job.document_type,
        status=job.status.value if hasattr(job.status, "value") else job.status,
        structured_output=job.structured_output,
        conflicts=job.conflicts or [],
        completed_at=job.completed_at
    )


@router.get("/extraction-jobs/{job_id}", response_model=ExtractionJobResponse)
def get_extraction_job(job_id: UUID, db: Session = Depends(get_db)):
    """Poll for extraction result"""
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction job not found")

    return ExtractionJobResponse(
        id=job.id,
        vendor_id=job.vendor_id,
        document_type=job.document_type,
        status=job.status.value if hasattr(job.status, "value") else job.status,
        structured_output=job.structured_output,
        conflicts=job.conflicts or [],
        completed_at=job.completed_at
    )


@router.get("/vendors/{vendor_id}/evidence")
def get_vendor_evidence(vendor_id: UUID, db: Session = Depends(get_db)):
    """
    Lists raw EvidenceSignal records for a vendor.

    These are signals from breach-DB, public-records, status-API, separate from document extractions.
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    signals = db.query(EvidenceSignal).filter(
        EvidenceSignal.vendor_id == vendor_id
    ).order_by(EvidenceSignal.received_at.desc()).limit(50).all()

    items = [
        EvidenceSignalResponse(
            id=signal.id,
            source=signal.source,
            signal_type=signal.signal_type,
            received_at=signal.received_at,
            payload=signal.payload,
            consumed_by_score_id=signal.consumed_by_score_id
        )
        for signal in signals
    ]

    return {"items": items}
