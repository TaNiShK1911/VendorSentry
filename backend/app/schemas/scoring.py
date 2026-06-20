"""
Pydantic schemas for scoring responses.
Matches BACKEND_INTEGRATION.md §3 exactly.

ARCHITECTURAL RULE: composite_score, tier, and status_color in these
schemas are always populated by the deterministic scoring engine —
never by LLM output.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class SubscoreBreakdown(BaseModel):
    breach_subscore: float
    access_subscore: float
    compliance_subscore: float
    financial_subscore: float


class ScoreWeights(BaseModel):
    breach: float = 0.40
    access: float = 0.25
    compliance: float = 0.20
    financial: float = 0.15


class PreviousScoreSummary(BaseModel):
    composite_score: float
    tier: str
    status_color: str
    computed_at: datetime


class VendorScoreOut(BaseModel):
    """Full score breakdown — returned by GET /vendors/{id}/score."""
    id: str
    vendor_id: str
    computed_at: datetime
    composite_score: float
    tier: str            # CRITICAL | HIGH | MEDIUM | LOW | CLEAR
    status_color: str    # RED | YELLOW | GREEN
    subscores: SubscoreBreakdown
    weights: ScoreWeights = Field(default_factory=ScoreWeights)
    anomaly_types: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    triggered_by: str
    previous_score: Optional[PreviousScoreSummary] = None

    model_config = {"from_attributes": True}


class PortfolioScoreDistribution(BaseModel):
    """Returned by GET /portfolio/score-distribution."""
    by_tier: Dict[str, int]
    by_status_color: Dict[str, int]
    total_vendors: int
    as_of: datetime


class ScoreTrendPoint(BaseModel):
    date: str   # ISO date string e.g. "2026-05-01"
    by_tier: Dict[str, int]


class PortfolioScoreTrend(BaseModel):
    """Returned by GET /portfolio/score-trend."""
    points: List[ScoreTrendPoint]


class EvaluationTierMetrics(BaseModel):
    precision: float
    recall: float
    f1: float


class EvaluationResult(BaseModel):
    """Returned by GET /admin/evaluation."""
    run_at: datetime
    overall_accuracy: float
    by_tier: Dict[str, EvaluationTierMetrics]
