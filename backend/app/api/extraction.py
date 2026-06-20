"""Extraction and evidence API endpoints"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vendor, ExtractionJob, EvidenceSignal
from app.services.extraction.contract_parser import extract_contract

router = APIRouter()


@router.post("/vendors/{vendor_id}/extract", status_code=status.HTTP_202_ACCEPTED)
async def extract_document(
    vendor_id: str,
    document_type: str = Form(...),
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
        if file.filename and file.filename.lower().endswith('.pdf'):
            import io
            import PyPDF2
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                text_pages = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_pages.append(page_text)
                raw_text = "\n".join(text_pages)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to parse PDF: {e}"
                )
        else:
            raw_text = content.decode('utf-8', errors='ignore')
    elif text:
        raw_text = text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text or file must be provided"
        )

    try:
        job = extract_contract(vendor, raw_text, db, document_type)

    except Exception as e:
        # extract_contract should handle exceptions and set job.status="failed"
        # but in case something slips through:
        job = ExtractionJob(
            vendor_id=vendor_id,
            source_type=document_type,
            document_type=document_type,
            raw_text=raw_text,
            status="failed",
            error_message=str(e),
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.add(job)
        db.flush()

    return {
        "job_id": job.id,
        "status": job.status,
        "progress_percent": 100 if job.status == "done" else 0,
        "stage": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": {
            "extracted_data": job.structured_output or {},
            "conflicts": job.flagged_conflicts or [],
            "risk_flags": [],
            "confidence_score": job.confidence or 0.85,
        } if job.status == "done" else None,
        "error": {
            "code": "EXTRACTION_FAILED",
            "message": job.error_message or "Unknown error",
            "stage": "processing",
        } if job.status == "failed" else None,
    }


@router.get("/extraction-jobs/{job_id}")
def get_extraction_job(job_id: str, db: Session = Depends(get_db)):
    """Poll for extraction result"""
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "progress_percent": 100 if job.status == "done" else 0,
        "stage": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": {
            "extracted_data": job.structured_output or {},
            "conflicts": job.flagged_conflicts or [],
            "risk_flags": [],
            "confidence_score": job.confidence or 0.85,
        } if job.status == "done" else None,
    }


@router.get("/vendors/{vendor_id}/evidence")
def get_vendor_evidence(vendor_id: str, db: Session = Depends(get_db)):
    """Lists raw EvidenceSignal records for a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    signals = db.query(EvidenceSignal).filter(
        EvidenceSignal.vendor_id == vendor_id
    ).order_by(EvidenceSignal.received_at.desc()).limit(50).all()

    items = [
        {
            "id": signal.id,
            "source": signal.source,
            "signal_type": signal.signal_type,
            "received_at": signal.received_at.isoformat() if signal.received_at else None,
            "payload": signal.payload,
            "consumed_by_score_id": signal.consumed_by_score_id,
        }
        for signal in signals
    ]

    return {"items": items}
