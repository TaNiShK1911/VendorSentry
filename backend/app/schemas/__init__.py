from app.schemas.vendor import (
    VendorCreate, VendorUpdate, VendorListItem, VendorDetail,
    ImportResult, CertificationOut, BreachEventOut, DataAccessScopeOut, ContactInfo
)
from app.schemas.scoring import (
    VendorScoreOut, PortfolioScoreDistribution, ScoreTrendPoint,
    PortfolioScoreTrend, EvaluationResult, EvaluationTierMetrics,
    SubscoreBreakdown, ScoreWeights, PreviousScoreSummary
)
from app.schemas.extraction import (
    ExtractionJobCreate, ExtractionJobOut, StructuredExtractionOutput,
    ConflictRecord, EvidenceSignalOut
)
from app.schemas.alert import AlertOut, AlertSummary, AlertResolveRequest
from app.schemas.common import PaginatedResponse, LoginRequest, LoginResponse, TokenData

# Aliases for backward compatibility with Dev B API naming
AlertResponse = AlertOut
AlertResolve = AlertResolveRequest
ExtractionJobResponse = ExtractionJobOut
EvidenceSignalResponse = EvidenceSignalOut
VendorScoreResponse = VendorScoreOut
VendorContact = ContactInfo
VendorScoreSubscores = SubscoreBreakdown
VendorScoreWeights = ScoreWeights
VendorScorePrevious = PreviousScoreSummary
PortfolioTrendPoint = ScoreTrendPoint

__all__ = [
    "VendorCreate", "VendorUpdate", "VendorListItem", "VendorDetail",
    "ImportResult", "CertificationOut", "BreachEventOut", "DataAccessScopeOut",
    "ContactInfo", "VendorContact",
    "VendorScoreOut", "VendorScoreResponse", "PortfolioScoreDistribution", "ScoreTrendPoint",
    "PortfolioScoreTrend", "PortfolioTrendPoint", "EvaluationResult", "EvaluationTierMetrics",
    "SubscoreBreakdown", "VendorScoreSubscores", "ScoreWeights", "VendorScoreWeights",
    "PreviousScoreSummary", "VendorScorePrevious",
    "ExtractionJobCreate", "ExtractionJobOut", "ExtractionJobResponse", "StructuredExtractionOutput",
    "ConflictRecord", "EvidenceSignalOut", "EvidenceSignalResponse",
    "AlertOut", "AlertResponse", "AlertSummary", "AlertResolveRequest", "AlertResolve",
    "PaginatedResponse", "LoginRequest", "LoginResponse", "TokenData",
]
