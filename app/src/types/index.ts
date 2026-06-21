// ============================================================
// VendorSentry — TypeScript Type Definitions
// ============================================================

// ---- Authentication ----

export interface User {
  id: string;
  email: string;
  name: string;
  first_name?: string;
  last_name?: string;
  role: 'ciso' | 'procurement' | 'auditor';
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  user: User;
}

// ---- Vendors ----

export type VendorType = 'cloud_provider' | 'contractor' | 'mss_provider' | 'payment_processor' | 'software_vendor' | 'other' | string;

export type StatusColor = 'RED' | 'YELLOW' | 'GREEN';

export type RiskTier = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'CLEAR';

export interface Vendor {
  id: string;
  name: string;
  vendor_type: VendorType;
  contact_email: string;
  website_domain?: string;
  annual_spend: number;
  contract_start: string;
  contract_end: string;
  has_pii_access: boolean;
  has_financial_access: boolean;
  systems_access: string[];
  data_access_notes: string;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
  composite_score: number;
  status_color: StatusColor;
  risk_tier: RiskTier;
  active_alerts: number;
  last_assessed: string | null;
  contract_days_remaining?: number;
}

export interface VendorCreateRequest {
  name: string;
  vendor_type: VendorType | string;
  contact_email: string;
  website_domain?: string;
  annual_spend?: number;
  contract_start?: string;
  contract_end?: string;
  has_pii_access?: boolean;
  has_financial_access?: boolean;
  systems_access?: string[];
  data_access_notes?: string;
  status?: 'active' | 'inactive';
}

export interface VendorUpdateRequest {
  name?: string;
  vendor_type?: VendorType | string;
  contact_email?: string;
  website_domain?: string;
  annual_spend?: number;
  contract_start?: string;
  contract_end?: string;
  has_pii_access?: boolean;
  has_financial_access?: boolean;
  systems_access?: string[];
  data_access_notes?: string;
  status?: 'active' | 'inactive';
}

export interface VendorListResponse {
  vendors: Vendor[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

// ---- Risk Scoring ----

export interface Subscore {
  score: number;
  weight: number;
  weighted_score: number;
  factors: string[];
}

export interface ScoreHistoryEntry {
  date: string;
  score: number;
  tier: RiskTier;
  reason: string;
}

export interface VendorScore {
  vendor_id: string;
  vendor_name: string;
  composite_score: number;
  status_color: StatusColor;
  risk_tier: RiskTier;
  previous_score: number;
  score_delta: number;
  assessed_at: string;
  subscores: {
    breach_risk: Subscore;
    access_risk: Subscore;
    compliance_risk: Subscore;
    financial_risk: Subscore;
  };
  anomaly_types: string[];
  trigger_sources: string[];
  rationale: string;
  score_history: ScoreHistoryEntry[];
}

// ---- Certifications ----

export type CertStatus = 'active' | 'expiring_soon' | 'expired';

export interface Certification {
  id: string;
  name: string;
  status: CertStatus;
  issue_date: string;
  expiry_date: string;
  source: string;
  days_until_expiry: number;
}

export interface VendorCertifications {
  vendor_id: string;
  certifications: Certification[];
}

// ---- Breaches ----

export interface Breach {
  id: string;
  date: string;
  source: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  records_affected: number;
}

export interface VendorBreaches {
  vendor_id: string;
  breaches: Breach[];
}

// ---- Evidence ----

export interface EvidencePayload {
  matched: boolean;
  [key: string]: unknown;
}

export interface EvidenceSource {
  source: string;
  matched: boolean;
  last_checked: string;
  risk_signal: string;
  payload: EvidencePayload;
}

export interface VendorEvidence {
  vendor_id: string;
  evidence_sources: {
    breach_db: EvidenceSource;
    public_records: EvidenceSource;
    status_api: EvidenceSource;
  };
}

// ---- Portfolio ----

export interface ScoreDistribution {
  by_status_color: {
    RED: number;
    YELLOW: number;
    GREEN: number;
  };
  by_tier: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    CLEAR: number;
  };
  total_vendors: number;
  avg_composite_score: number;
  median_score: number;
  highest_score: number;
  lowest_score: number;
}

export interface TrendDataPoint {
  date: string;
  avg_score: number;
  risk_vendor_count: number;
  total_vendors: number;
}

export interface ScoreTrend {
  range: string;
  data_points: TrendDataPoint[];
}

// ---- Alerts ----

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';
export type AlertStatus = 'open' | 'acknowledged' | 'resolved';
export type AlertType = 'CERT_EXPIRING' | 'CONTRACT_EXPIRING' | 'ASSESSMENT_OVERDUE' | 'NEW_BREACH' | 'SCORE_TIER_CHANGED';

export interface Alert {
  id: string;
  vendor_id: string;
  vendor_name: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface AlertListResponse {
  alerts: Alert[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

export interface AlertSummary {
  total_open: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  by_type: {
    CERT_EXPIRING: number;
    CONTRACT_EXPIRING: number;
    ASSESSMENT_OVERDUE: number;
    NEW_BREACH: number;
    SCORE_TIER_CHANGED: number;
  };
  recent_alerts: number;
  trend: 'increasing' | 'decreasing' | 'stable';
}

// ---- Document Extraction ----

export type DocumentType = 'contract' | 'security_assessment' | 'audit_report';
export type ExtractionStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ExtractionJob {
  job_id: string;
  status: ExtractionStatus;
  progress_percent: number;
  stage?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  failed_at?: string;
  error?: {
    code: string;
    message: string;
    stage: string;
  };
  result?: ExtractionResult;
}

export interface ExtractionConflict {
  field: string;
  expected?: unknown;
  extracted?: unknown;
  claimed?: unknown;
  actual_on_record?: unknown;
  severity?: 'high' | 'medium' | 'low' | string;
  description?: string;
  note?: string;
}

export interface RiskFlag {
  type: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  clause_reference?: string;
}

export interface ExtractionResult {
  extracted_data: Record<string, unknown>;
  conflicts: ExtractionConflict[];
  risk_flags: RiskFlag[];
  confidence_score: number;
}

// ---- Evaluation ----

export interface SeverityTierMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  sample_count: number;
}

export interface EvaluationMetrics {
  evaluated_at: string;
  dataset_info: {
    total_vendors_evaluated: number;
    ground_truth_available: number;
    evaluation_period: string;
  };
  overall_metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    mae: number;
    rmse: number;
  };
  by_severity_tier: {
    CRITICAL: SeverityTierMetrics;
    HIGH: SeverityTierMetrics;
    MEDIUM: SeverityTierMetrics;
    LOW: SeverityTierMetrics;
    CLEAR: SeverityTierMetrics;
  };
  confusion_matrix: {
    predicted: string[];
    actual: string[];
    matrix: number[][];
  };
  score_distribution: {
    bins: string[];
    predicted: number[];
    actual: number[];
  };
}

// ---- API Error ----

export interface ApiError {
  detail: string;
  code: string;
  timestamp: string;
}

// ---- Filter / Query Params ----

export interface VendorFilters {
  search?: string;
  tier?: string;
  type?: string;
  score_min?: number;
  score_max?: number;
  has_pii?: boolean;
  cert_expiry_before?: string;
}

export interface AlertFilters {
  status?: AlertStatus;
  severity?: AlertSeverity;
  vendor_id?: string;
  alert_type?: AlertType;
}

export interface SortOption {
  value: string;
  label: string;
}

export const VENDOR_SORT_OPTIONS: SortOption[] = [
  { value: 'score_desc', label: 'Score (High → Low)' },
  { value: 'score_asc', label: 'Score (Low → High)' },
  { value: 'name_asc', label: 'Name (A → Z)' },
  { value: 'alerts_desc', label: 'Alerts (Most)' },
  { value: 'assessed_desc', label: 'Recently Assessed' },
  { value: 'created_desc', label: 'Newest' },
];

export const VENDOR_TYPES: {value: string, label: string}[] = [
  { value: 'cloud_provider', label: 'Cloud Provider' },
  { value: 'contractor', label: 'Contractor' },
  { value: 'mss_provider', label: 'MSS Provider' },
  { value: 'payment_processor', label: 'Payment Processor' },
  { value: 'software_vendor', label: 'Software Vendor' },
  { value: 'other', label: 'Other' },
];

export const RISK_TIERS: RiskTier[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'CLEAR'];

export const ALERT_TYPES: AlertType[] = [
  'CERT_EXPIRING',
  'CONTRACT_EXPIRING',
  'ASSESSMENT_OVERDUE',
  'NEW_BREACH',
  'SCORE_TIER_CHANGED',
];
