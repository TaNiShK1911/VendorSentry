import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { vendorsApi, scoringApi } from '@/api';
import { useAuth } from '@/hooks/useAuth';
import {
  ArrowLeft, AlertTriangle, Database, KeyRound, FileCheck, Banknote,
  ChevronDown, ChevronUp, ShieldCheck,
  UploadCloud, Trash2, Edit3,
} from 'lucide-react';
import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import type { EvidenceSource } from '@/types';
import { VendorFormDialog } from '@/components/vendors/VendorFormDialog';

// ---- Evidence Card ----
function EvidenceCard({ source }: { source: EvidenceSource }) {
  const hasConflict = source.matched === false;

  return (
    <div className={`rounded-card border p-4 ${hasConflict ? 'border-vs-risk-red/20 bg-sg-risk-red-bg' : 'border-sg-border-subtle bg-white'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-display text-sm font-bold text-sg-text-primary">
            {source.source === 'breach_db' ? 'Breach Database'
              : source.source === 'public_records' ? 'Public Records'
              : 'Status API'}
          </span>
          <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
            source.matched ? 'bg-sg-risk-green-bg text-sg-risk-green' : 'bg-sg-risk-red-bg text-sg-risk-red'
          }`}>
            {source.matched ? 'Matched' : 'No Match'}
          </span>
        </div>
        <span className="text-[10px] text-sg-text-secondary">
          Checked: {new Date(source.last_checked).toLocaleDateString()}
        </span>
      </div>

      <p className="mt-2 text-sm text-sg-text-secondary">{source.risk_signal}</p>

      {hasConflict && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-vs-risk-red/20 bg-sg-risk-red/5 px-3 py-2">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-sg-risk-red" />
          <p className="text-xs text-sg-risk-red">
            Conflict Detected: {source.source} reports no match while other sources indicate risk.
          </p>
        </div>
      )}

      {/* Payload details */}
      <div className="mt-3 rounded border border-sg-border-subtle bg-sg-surface-muted p-2">
        <pre className="overflow-x-auto text-[10px] leading-relaxed text-sg-text-secondary" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
          {JSON.stringify(source.payload, null, 2)}
        </pre>
      </div>
    </div>
  );
}

// ---- Custom Chart Tooltip ----
function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-sg-border-subtle bg-sg-surface p-3 shadow-lg">
      <p className="text-xs text-sg-text-secondary">{label}</p>
      <p className="mt-1 text-sm font-bold text-sg-text-primary">Score: {payload[0].value}</p>
    </div>
  );
}

// ============================================================
// Vendor Detail Page
// ============================================================

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const vendorId = id!;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canEdit, canDelete } = useAuth();
  const [editOpen, setEditOpen] = useState(false);
  const [showRationale, setShowRationale] = useState(false);

  // Fetch all vendor data in parallel
  const { data: vendor, isLoading: vendorLoading } = useQuery({
    queryKey: ['vendors', 'detail', vendorId],
    queryFn: () => vendorsApi.getById(vendorId),
  });

  const { data: scoreData } = useQuery({
    queryKey: ['vendors', 'score', vendorId],
    queryFn: () => scoringApi.getVendorScore(vendorId),
  });

  const { data: certifications } = useQuery({
    queryKey: ['vendors', 'certifications', vendorId],
    queryFn: () => scoringApi.getVendorCertifications(vendorId),
  });

  const { data: breaches } = useQuery({
    queryKey: ['vendors', 'breaches', vendorId],
    queryFn: () => scoringApi.getVendorBreaches(vendorId),
  });

  const { data: evidence } = useQuery({
    queryKey: ['vendors', 'evidence', vendorId],
    queryFn: () => scoringApi.getVendorEvidence(vendorId),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => vendorsApi.delete(vendorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      navigate('/vendors');
    },
  });

  if (vendorLoading || !vendor) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin-slow rounded-full border-2 border-black/10 border-t-vs-accent-blue" />
      </div>
    );
  }

  const score = scoreData;
  const hasConflicts = evidence?.evidence_sources && Object.values(evidence.evidence_sources).some((s) => !s.matched);

  const getScoreColor = (s: number) => {
    if (s >= 70) return '#F85151';
    if (s >= 40) return '#E8A838';
    return '#1DB954';
  };

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'CRITICAL': return 'tier-badge-critical';
      case 'HIGH': return 'tier-badge-high';
      case 'MEDIUM': return 'tier-badge-medium';
      case 'LOW': return 'tier-badge-low';
      case 'CLEAR': return 'tier-badge-clear';
      default: return 'tier-badge-clear';
    }
  };

  const scoreColor = getScoreColor(score?.composite_score || 0);
  const circumference = 2 * Math.PI * 50;
  const strokeDashoffset = circumference - ((score?.composite_score || 0) / 100) * circumference;

  // Prepare chart data
  const chartData = score?.score_history.map((h) => ({
    date: new Date(h.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
    score: h.score,
    fullDate: h.date,
  })) || [];

  return (
    <div className="p-8">
      {/* Breadcrumb + Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/vendors')}
          className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-sg-text-secondary transition-colors hover:text-sg-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Vendors
        </button>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/vendors/${vendorId}/extract`)}
            className="flex items-center gap-2 rounded-button border border-sg-border-subtle bg-white px-4 py-2.5 text-sm font-medium text-sg-text-secondary transition-all hover:border-sg-border-focus hover:text-sg-text-primary"
          >
            <UploadCloud className="h-4 w-4" />
            Extract Document
          </button>
          {canEdit && (
            <button
              onClick={() => setEditOpen(true)}
              className="flex items-center gap-2 rounded-button border border-sg-border-subtle bg-white px-4 py-2.5 text-sm font-medium text-sg-text-secondary transition-all hover:border-sg-border-focus hover:text-sg-text-primary"
            >
              <Edit3 className="h-4 w-4" />
              Edit
            </button>
          )}
          {canDelete && (
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to delete this vendor?')) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-2 rounded-button border border-vs-risk-red/20 bg-sg-risk-red-bg px-4 py-2.5 text-sm font-medium text-sg-risk-red transition-all hover:bg-sg-risk-red-bg"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          )}
        </div>
      </div>

      {/* ====== SECTION A: Vendor Overview ====== */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
      >
        {/* Name + Tier + Score */}
        <div className="flex flex-wrap items-center gap-4">
          <h1 className="font-display text-3xl font-bold uppercase text-sg-text-primary">{vendor.name}</h1>
          <span className={`status-dot h-4 w-4 ${vendor.status_color === 'RED' ? 'status-dot-red' : vendor.status_color === 'YELLOW' ? 'status-dot-yellow' : 'status-dot-green'}`} />
          <span className={`rounded-lg px-4 py-1.5 text-xs font-bold uppercase ${getTierBadge(vendor.risk_tier)}`}>
            {vendor.risk_tier}
          </span>
        </div>

        {/* Info grid */}
        <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Type</p>
            <p className="mt-1 text-sm font-medium text-sg-text-primary">{vendor.vendor_type}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Contact</p>
            <p className="mt-1 text-sm text-sg-text-secondary">{vendor.contact_email}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Annual Spend</p>
            <p className="mt-1 text-sm text-sg-text-primary">
              ${vendor.annual_spend?.toLocaleString() || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Contract Status</p>
            <div className="mt-1 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-sg-risk-green" />
              <span className="text-sm capitalize text-sg-risk-green">{vendor.status}</span>
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Contract Start</p>
            <p className="mt-1 text-sm text-sg-text-secondary">
              {vendor.contract_start ? new Date(vendor.contract_start).toLocaleDateString() : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Contract End</p>
            <p className="mt-1 text-sm text-sg-text-secondary">
              {vendor.contract_end ? new Date(vendor.contract_end).toLocaleDateString() : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Days Remaining</p>
            <p className={`mt-1 text-sm font-medium ${(vendor.contract_days_remaining || 0) < 90 ? 'text-sg-risk-red' : 'text-sg-text-secondary'}`}>
              {vendor.contract_days_remaining || 'N/A'}
            </p>
          </div>
        </div>
      </motion.div>

      {/* ====== SECTION B: Risk Header ====== */}
      {score && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
        >
          <div className="flex flex-wrap items-center gap-8">
            {/* Score circle */}
            <div className="relative flex h-32 w-32 items-center justify-center">
              <svg className="h-32 w-32 -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" fill="none" stroke="#e2e2e2" strokeWidth="6" />
                <circle
                  cx="60" cy="60" r="50" fill="none"
                  stroke={scoreColor}
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  className="transition-all duration-1000"
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                <span className="text-3xl font-bold" style={{ color: scoreColor }}>
                  {score.composite_score}
                </span>
                <span className="text-[10px] uppercase tracking-wider text-sg-text-secondary">Score</span>
              </div>
            </div>

            {/* Score summary */}
            <div className="flex-1">
              <p className="text-lg text-sg-text-primary">
                This vendor is rated <span className="font-bold" style={{ color: scoreColor }}>{score.risk_tier}</span> with a composite score of <span className="font-bold" style={{ color: scoreColor }}>{score.composite_score}</span>.
              </p>
              <div className="mt-2 flex items-center gap-3">
                <span className="text-sm text-sg-text-secondary">Previous: {score.previous_score}</span>
                <span className={`flex items-center gap-1 text-sm font-medium ${score.score_delta > 0 ? 'text-sg-risk-red' : 'text-sg-risk-green'}`}>
                  {score.score_delta > 0 ? '↑' : '↓'} {Math.abs(score.score_delta)}
                </span>
              </div>
              <p className="mt-2 text-sm text-sg-text-secondary">{score.rationale.substring(0, 200)}...</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* ====== SECTION C: Risk Breakdown ====== */}
      {score && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
        >
          <h2 className="font-display text-lg font-bold uppercase tracking-wider text-sg-text-primary">Risk Score Breakdown</h2>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { key: 'breach_risk', label: 'Breach Risk', icon: Database, weight: 30 },
              { key: 'access_risk', label: 'Access Risk', icon: KeyRound, weight: 25 },
              { key: 'compliance_risk', label: 'Compliance Risk', icon: FileCheck, weight: 25 },
              { key: 'financial_risk', label: 'Financial Risk', icon: Banknote, weight: 20 },
            ].map((item) => {
              const sub = score.subscores[item.key as keyof typeof score.subscores];
              const subColor = getScoreColor(sub.score);
              const Icon = item.icon;
              return (
                <div key={item.key} className="rounded-lg border border-sg-border-subtle bg-sg-surface-muted p-4">
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4" style={{ color: subColor }} />
                    <span className="font-display text-sm font-bold uppercase tracking-wider text-sg-text-primary">{item.label}</span>
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-2xl font-bold" style={{ color: subColor }}>{sub.score}</span>
                    <span className="text-xs text-sg-text-secondary">/100</span>
                  </div>
                  <p className="mt-1 text-xs text-sg-text-secondary">Weight: {sub.weight * 100}%</p>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-sg-border-subtle">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${sub.score}%`, backgroundColor: subColor }}
                    />
                  </div>
                  <div className="mt-2 space-y-0.5">
                    {sub.factors.slice(0, 2).map((f, i) => (
                      <p key={i} className="text-[10px] text-sg-text-secondary">• {f}</p>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Anomaly types */}
          {score.anomaly_types.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs text-sg-text-secondary">Anomalies:</span>
              {score.anomaly_types.map((a) => (
                <span key={a} className="rounded bg-sg-risk-yellow-bg px-2 py-1 text-xs font-medium text-sg-risk-yellow">
                  {a}
                </span>
              ))}
            </div>
          )}

          {/* Trigger sources */}
          <div className="mt-2">
            <span className="text-xs text-sg-text-secondary">Sources: </span>
            <span className="font-mono text-xs text-sg-text-secondary">
              {score.trigger_sources.join(', ')}
            </span>
          </div>

          {/* Full Rationale */}
          <div className="mt-4">
            <button
              onClick={() => setShowRationale(!showRationale)}
              className="flex items-center gap-1 text-sm text-sg-text-primary hover:underline"
            >
              {showRationale ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              {showRationale ? 'Hide' : 'Show'} Full Rationale
            </button>
            {showRationale && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-2 rounded-lg border border-sg-border-subtle bg-sg-surface-muted p-4 text-sm leading-relaxed text-sg-text-secondary"
              >
                {score.rationale}
              </motion.div>
            )}
          </div>
        </motion.div>
      )}

      {/* ====== SECTION D: Certifications Timeline ====== */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
      >
        <h2 className="font-display text-lg font-bold uppercase tracking-wider text-sg-text-primary">Certifications</h2>
        {certifications?.certifications.length === 0 ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-sg-text-secondary">
            <ShieldCheck className="h-5 w-5 text-sg-risk-green" />
            No certifications recorded.
          </div>
        ) : (
          <div className="relative mt-4 pl-6">
            {/* Vertical line */}
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-sg-border-subtle" />
            <div className="space-y-4">
              {certifications?.certifications.map((cert) => {
                const dotColor = cert.status === 'active' ? '#1DB954' : cert.status === 'expiring_soon' ? '#E8A838' : '#F85151';
                return (
                  <div key={cert.id} className="relative">
                    <div
                      className="absolute -left-6 top-1.5 h-3 w-3 rounded-full border-2 border-vs-bg-surface"
                      style={{ backgroundColor: dotColor }}
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-display text-sm font-bold text-sg-text-primary">{cert.name}</span>
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                          cert.status === 'active' ? 'bg-sg-risk-green-bg text-sg-risk-green'
                          : cert.status === 'expiring_soon' ? 'bg-sg-risk-yellow-bg text-sg-risk-yellow'
                          : 'bg-sg-risk-red-bg text-sg-risk-red'
                        }`}>
                          {cert.status === 'expiring_soon' ? 'Expiring Soon' : cert.status}
                        </span>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-3 font-mono text-[11px] text-sg-text-secondary">
                        <span>Issued: {new Date(cert.issue_date).toLocaleDateString()}</span>
                        <span>Expires: {new Date(cert.expiry_date).toLocaleDateString()}</span>
                        <span>Source: {cert.source}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </motion.div>

      {/* ====== SECTION E: Breach History ====== */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
      >
        <h2 className="font-display text-lg font-bold uppercase tracking-wider text-sg-text-primary">Breach History</h2>
        {breaches?.breaches.length === 0 ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-sg-risk-green">
            <ShieldCheck className="h-5 w-5" />
            No breach incidents recorded.
          </div>
        ) : (
          <div className="relative mt-4 pl-6">
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-sg-border-subtle" />
            <div className="space-y-4">
              {breaches?.breaches.map((breach) => (
                <div key={breach.id} className="relative">
                  <div className="absolute -left-6 top-1.5 h-3 w-3 rounded-full border-2 border-vs-bg-surface bg-sg-risk-red" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-display text-sm font-bold text-sg-text-primary">
                        {new Date(breach.date).toLocaleDateString()}
                      </span>
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                        breach.severity === 'critical' ? 'bg-sg-risk-red-bg text-sg-risk-red'
                        : 'bg-sg-risk-yellow-bg text-sg-risk-yellow'
                      }`}>
                        {breach.severity}
                      </span>
                      <span className="text-[10px] text-sg-text-secondary">({breach.source})</span>
                    </div>
                    <p className="mt-1 text-sm text-sg-text-secondary">{breach.description}</p>
                    {breach.records_affected > 0 && (
                      <p className="mt-0.5 text-xs text-sg-text-secondary">
                        {breach.records_affected.toLocaleString()} records affected
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* ====== SECTION F: Data Access Scope ====== */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
      >
        <h2 className="font-display text-lg font-bold uppercase tracking-wider text-sg-text-primary">Data Access Scope</h2>
        <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="rounded-lg border border-sg-border-subtle bg-sg-surface-muted p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">PII Access</p>
            <div className="mt-2 flex items-center gap-2">
              {vendor.has_pii_access ? (
                <>
                  <AlertTriangle className="h-5 w-5 text-sg-risk-yellow" />
                  <span className="font-medium text-sg-risk-yellow">Yes</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="h-5 w-5 text-sg-risk-green" />
                  <span className="font-medium text-sg-risk-green">No</span>
                </>
              )}
            </div>
          </div>
          <div className="rounded-lg border border-sg-border-subtle bg-sg-surface-muted p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Financial Data</p>
            <div className="mt-2 flex items-center gap-2">
              {vendor.has_financial_access ? (
                <>
                  <AlertTriangle className="h-5 w-5 text-sg-risk-yellow" />
                  <span className="font-medium text-sg-risk-yellow">Yes</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="h-5 w-5 text-sg-risk-green" />
                  <span className="font-medium text-sg-risk-green">No</span>
                </>
              )}
            </div>
          </div>
          <div className="rounded-lg border border-sg-border-subtle bg-sg-surface-muted p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Systems Access</p>
            <div className="mt-2">
              {vendor.systems_access?.length ? (
                <div className="flex flex-wrap gap-1">
                  {vendor.systems_access.map((s) => (
                    <span key={s} className="rounded bg-sg-surface px-2 py-0.5 text-xs text-sg-text-secondary">{s}</span>
                  ))}
                </div>
              ) : (
                <span className="text-sm text-sg-text-secondary">None</span>
              )}
            </div>
          </div>
          <div className="rounded-lg border border-sg-border-subtle bg-sg-surface-muted p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Notes</p>
            <p className="mt-2 text-xs text-sg-text-secondary">{vendor.data_access_notes || 'No notes'}</p>
          </div>
        </div>
      </motion.div>

      {/* ====== SECTION G: Evidence Trail ====== */}
      {evidence?.evidence_sources && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-6"
        >
          {/* Conflict Banner */}
          {hasConflicts && (
            <div className="mb-4 rounded-card conflict-banner p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-6 w-6 flex-shrink-0 text-sg-risk-red" />
                <div>
                  <h3 className="text-lg font-semibold text-sg-risk-red">Evidence Conflicts Detected</h3>
                  <p className="mt-1 text-sm text-sg-text-secondary">
                    One or more evidence sources report conflicting data. Review the evidence cards below for details.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="rounded-card border border-sg-border-subtle bg-white p-6 shadow-card">
            <h2 className="font-display text-lg font-bold uppercase tracking-wider text-sg-text-primary">Evidence Sources</h2>
            <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
              <EvidenceCard source={evidence.evidence_sources.breach_db} />
              <EvidenceCard source={evidence.evidence_sources.public_records} />
              <EvidenceCard source={evidence.evidence_sources.status_api} />
            </div>
          </div>
        </motion.div>
      )}

      {/* ====== SECTION H: Risk Trend Chart ====== */}
      {chartData.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
        >
          <h2 className="font-display text-lg font-bold uppercase tracking-wider text-sg-text-primary">Risk Score History</h2>
          <div className="mt-4">
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <defs>
                  <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={scoreColor} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={scoreColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e2e2" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#5A5E72', fontSize: 11 }}
                  axisLine={{ stroke: '#BDBDBD' }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: '#5A5E72', fontSize: 11 }}
                  axisLine={{ stroke: '#BDBDBD' }}
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="score"
                  stroke={scoreColor}
                  strokeWidth={2}
                  fill="url(#scoreGradient)"
                  animationDuration={1000}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      )}

      {/* ====== SECTION I: Audit History ====== */}
      {score?.score_history && score.score_history.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-6 rounded-card border border-sg-border-subtle bg-white p-6 shadow-card"
        >
          <h2 className="font-display text-lg font-bold uppercase tracking-wider text-sg-text-primary">Score Changes</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-sg-border-subtle">
                  <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Date</th>
                  <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Previous Score</th>
                  <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">New Score</th>
                  <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Delta</th>
                  <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Reason</th>
                </tr>
              </thead>
              <tbody>
                {score.score_history.map((entry, i) => {
                  const prev = i > 0 ? score.score_history[i - 1].score : entry.score;
                  const delta = entry.score - prev;
                  return (
                    <tr key={i} className="border-b border-sg-border-subtle">
                      <td className="py-3 text-sm text-sg-text-secondary">
                        {new Date(entry.date).toLocaleDateString()}
                      </td>
                      <td className="py-3 text-sm text-sg-text-secondary">{prev}</td>
                      <td className="py-3 text-sm font-medium text-sg-text-primary">{entry.score}</td>
                      <td className="py-3">
                        <span className={`text-sm font-medium ${delta > 0 ? 'text-sg-risk-red' : delta < 0 ? 'text-sg-risk-green' : 'text-sg-text-secondary'}`}>
                          {delta > 0 ? '↑' : delta < 0 ? '↓' : '→'} {Math.abs(delta)}
                        </span>
                      </td>
                      <td className="py-3 text-sm text-sg-text-secondary">{entry.reason}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* Edit Dialog */}
      <VendorFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        vendor={vendor}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['vendors', 'detail', vendorId] });
        }}
      />
    </div>
  );
}
