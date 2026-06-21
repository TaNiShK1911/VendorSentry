"""Evaluation API endpoint — returns model evaluation metrics"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()

@router.get("/admin/evaluation")
def get_evaluation_metrics(db: Session = Depends(get_db)):
    """
    Return evaluation metrics for the scoring model.
    Runs the live evaluation script against ground truth data.
    """
    import sys
    from pathlib import Path
    
    # Ensure backend is importable from repo root
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
        
    try:
        from scripts.evaluate import run_evaluation
        return run_evaluation(db)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Evaluation failed: {str(e)}"}

