"""Evaluation API endpoint — returns model evaluation metrics"""
from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/admin/evaluation")
def get_evaluation_metrics():
    """
    Return evaluation metrics for the scoring model.
    In production, this would run evaluate.py and return real metrics.
    For hackathon, returns representative mock data.
    """
    return {
        "evaluated_at": datetime.utcnow().isoformat(),
        "dataset_info": {
            "total_vendors_evaluated": 20,
            "ground_truth_available": 20,
            "evaluation_period": "2024-01-01 to 2024-12-31",
        },
        "overall_metrics": {
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.85,
            "mae": 8.2,
            "rmse": 12.5,
        },
        "by_severity_tier": {
            "CRITICAL": {
                "accuracy": 0.90,
                "precision": 0.88,
                "recall": 0.92,
                "f1_score": 0.90,
                "sample_count": 3,
            },
            "HIGH": {
                "accuracy": 0.85,
                "precision": 0.82,
                "recall": 0.88,
                "f1_score": 0.85,
                "sample_count": 5,
            },
            "MEDIUM": {
                "accuracy": 0.80,
                "precision": 0.78,
                "recall": 0.82,
                "f1_score": 0.80,
                "sample_count": 6,
            },
            "LOW": {
                "accuracy": 0.88,
                "precision": 0.86,
                "recall": 0.90,
                "f1_score": 0.88,
                "sample_count": 4,
            },
            "CLEAR": {
                "accuracy": 0.92,
                "precision": 0.90,
                "recall": 0.94,
                "f1_score": 0.92,
                "sample_count": 2,
            },
        },
        "confusion_matrix": {
            "predicted": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAR"],
            "actual": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAR"],
            "matrix": [
                [3, 0, 0, 0, 0],
                [0, 4, 1, 0, 0],
                [0, 1, 5, 0, 0],
                [0, 0, 0, 4, 0],
                [0, 0, 0, 0, 2],
            ],
        },
        "score_distribution": {
            "bins": ["0-20", "20-40", "40-60", "60-80", "80-100"],
            "predicted": [2, 4, 6, 5, 3],
            "actual": [2, 3, 7, 5, 3],
        },
    }
