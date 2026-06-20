from app.core.celery_app import celery_app
import logging

from app.core.database import SessionLocal
from app.models.vendor import Vendor
from app.models.extraction_job import ExtractionJob
from app.services.extraction.contract_parser import extract_contract

logger = logging.getLogger(__name__)

@celery_app.task(name="app.services.extraction.tasks.run_extraction_task")
def run_extraction_task(job_id: str, vendor_id: str, document_text: str, document_type: str):
    """
    Background task to execute LLM extraction.
    Loads the vendor and pending job, then calls extract_contract.
    """
    logger.info(f"Starting extraction task for job {job_id} on vendor {vendor_id}")
    db = SessionLocal()
    try:
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        
        if not vendor:
            logger.error(f"Vendor {vendor_id} not found for job {job_id}")
            if job:
                job.status = "failed"
                job.error_message = "Vendor not found"
                db.commit()
            return
            
        if not job:
            logger.error(f"Extraction job {job_id} not found")
            return
            
        # extract_contract updates the job fields internally
        extract_contract(vendor, job, document_text, db, document_type)
        db.commit()
        
    except Exception as e:
        logger.exception(f"Extraction task {job_id} failed with error: {e}")
        db.rollback()
        # Ensure job is marked as failed if an unhandled exception occurred
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()
