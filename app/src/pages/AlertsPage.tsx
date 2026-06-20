import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsApi } from '@/api';
import { useAuth } from '@/hooks/useAuth';
import {
  AlertTriangle, AlertCircle, Info, CheckCircle2,
  AlertOctagon, FileClock, Database, TrendingUp, Bell,
} from 'lucide-react';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';
import type { Alert, AlertSeverity, AlertStatus } from '@/types';

// ---- Alert Type Config ----
const ALERT_TYPE_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  CERT_EXPIRING: { label: 'Cert Expiring', color: '#E8A838', bg: 'rgba(232, 168, 56, 0.08)', icon: FileClock },
  CONTRACT_EXPIRING: { label: 'Contract Expiring', color: '#365DE5', bg: 'rgba(54, 93, 229, 0.08)', icon: AlertCircle },
  ASSESSMENT_OVERDUE: { label: 'Assessment Overdue', color: '#7C5CFC', bg: 'rgba(124, 92, 252, 0.08)', icon: Bell },
  NEW_BREACH: { label: 'New Breach', color: '#F85151', bg: 'rgba(248, 81, 81, 0.08)', icon: Database },
  SCORE_TIER_CHANGED: { label: 'Tier Changed', color: '#E8A838', bg: 'rgba(232, 168, 56, 0.08)', icon: TrendingUp },
};

const SEVERITY_CONFIG: Record<AlertSeverity, { color: string; icon: React.ElementType }> = {
  critical: { color: '#F85151', icon: AlertOctagon },
  high: { color: '#E8A838', icon: AlertTriangle },
  medium: { color: '#365DE5', icon: AlertCircle },
  low: { color: '#5A5E72', icon: Info },
};

// ---- Alert Card ----
function AlertCard({ alert, index }: { alert: Alert; index: number }) {
  const queryClient = useQueryClient();
  const { canAcknowledge } = useAuth();
  const [expanded, setExpanded] = useState(false);

  const typeConfig = ALERT_TYPE_CONFIG[alert.alert_type];
  const sevConfig = SEVERITY_CONFIG[alert.severity];
  const SevIcon = sevConfig.icon;

  const acknowledgeMutation = useMutation({
    mutationFn: () => alertsApi.acknowledge(alert.id),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['alerts'] });
      const prev = queryClient.getQueryData(['alerts']);
      queryClient.setQueryData(['alerts'], (old: any) => ({
        ...old,
        alerts: old.alerts.map((a: Alert) => a.id === alert.id ? { ...a, status: 'acknowledged' as AlertStatus } : a),
      }));
      return { prev };
    },
    onError: (_err, _vars, context) => {
      queryClient.setQueryData(['alerts'], context?.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['alerts', 'summary'] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => alertsApi.resolve(alert.id),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['alerts'] });
      const prev = queryClient.getQueryData(['alerts']);
      queryClient.setQueryData(['alerts'], (old: any) => ({
        ...old,
        alerts: old.alerts.map((a: Alert) => a.id === alert.id ? { ...a, status: 'resolved' as AlertStatus } : a),
      }));
      return { prev };
    },
    onError: (_err, _vars, context) => {
      queryClient.setQueryData(['alerts'], context?.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['alerts', 'summary'] });
    },
  });

  const isAcknowledged = alert.status === 'acknowledged';
  const isResolved = alert.status === 'resolved';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={`rounded-card border bg-white p-5 shadow-card transition-all hover:bg-white/[0.02] ${
        isResolved ? 'border-sg-border-subtle opacity-60' : 'border-sg-border-subtle'
      }`}
      style={!isResolved && !isAcknowledged ? { borderLeft: `3px solid ${sevConfig.color}` } : { borderLeft: `3px solid rgba(255,255,255,0.06)` }}
    >
      <div className="flex items-start gap-4">
        {/* Severity icon */}
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg" style={{ backgroundColor: `${sevConfig.color}10` }}>
          <SevIcon className="h-5 w-5" style={{ color: sevConfig.color }} />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="rounded px-2 py-0.5 text-[10px] font-semibold uppercase"
              style={{ backgroundColor: typeConfig.bg, color: typeConfig.color }}
            >
              {typeConfig.label}
            </span>
            <span className="cursor-pointer text-sm font-medium text-sg-text-primary hover:underline">
              {alert.vendor_name}
            </span>
            {isAcknowledged && (
              <span className="rounded bg-vs-text-tertiary/10 px-2 py-0.5 text-[10px] text-sg-text-secondary">
                Acknowledged
              </span>
            )}
            {isResolved && (
              <span className="rounded bg-sg-risk-green-bg px-2 py-0.5 text-[10px] text-sg-risk-green">
                Resolved
              </span>
            )}
          </div>

          <h3 className="mt-1 text-sm font-semibold text-sg-text-primary">{alert.title}</h3>
          <p className="mt-0.5 text-sm text-sg-text-secondary">{alert.message}</p>

          {expanded && alert.metadata && Object.keys(alert.metadata).length > 0 && (
            <div className="mt-2 rounded bg-sg-surface-muted border border-sg-border-subtle p-2">
              <pre className="overflow-x-auto text-[10px] text-sg-text-secondary" style={{ fontFamily: 'JetBrains Mono' }}>
                {JSON.stringify(alert.metadata, null, 2)}
              </pre>
            </div>
          )}

          <div className="mt-2 flex items-center gap-3">
            <span className="text-[10px] text-sg-text-secondary" style={{ fontFamily: 'JetBrains Mono' }}>
              {new Date(alert.created_at).toLocaleString()}
            </span>
            {Object.keys(alert.metadata).length > 0 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-[10px] text-sg-text-primary hover:underline"
              >
                {expanded ? 'Less' : 'More'} details
              </button>
            )}
          </div>
        </div>

        {/* Actions */}
        {canAcknowledge && !isResolved && (
          <div className="flex flex-shrink-0 flex-col gap-2">
            {!isAcknowledged && (
              <button
                onClick={() => acknowledgeMutation.mutate()}
                disabled={acknowledgeMutation.isPending}
                className="rounded-button border border-sg-border-subtle px-3 py-1.5 text-xs font-medium text-sg-text-secondary transition-all hover:bg-white/[0.04] hover:text-sg-text-primary disabled:opacity-50"
              >
                Acknowledge
              </button>
            )}
            <button
              onClick={() => resolveMutation.mutate()}
              disabled={resolveMutation.isPending}
              className="rounded-button border border-vs-risk-green/20 bg-sg-risk-green-bg px-3 py-1.5 text-xs font-medium text-sg-risk-green transition-all hover:bg-sg-risk-green-bg disabled:opacity-50"
            >
              Resolve
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ============================================================
// Alerts Page
// ============================================================

export default function AlertsPage() {
  const [statusFilter, setStatusFilter] = useState<AlertStatus | ''>('');
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | ''>('');
  const [page, setPage] = useState(1);

  const { data: summary } = useQuery({
    queryKey: ['alerts', 'summary'],
    queryFn: () => alertsApi.getSummary(),
    refetchInterval: 5000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', 'list', { page, status: statusFilter, severity: severityFilter }],
    queryFn: () => alertsApi.list({
      page,
      per_page: 20,
      ...(statusFilter && { status: statusFilter }),
      ...(severityFilter && { severity: severityFilter }),
    }),
  });

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight text-sg-text-primary">Alerts</h1>
      </div>

      {/* Severity cards */}
      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {([
          { label: 'Critical', severity: 'critical' as AlertSeverity, color: '#F85151', icon: AlertOctagon },
          { label: 'High', severity: 'high' as AlertSeverity, color: '#E8A838', icon: AlertTriangle },
          { label: 'Medium', severity: 'medium' as AlertSeverity, color: '#365DE5', icon: AlertCircle },
          { label: 'Low', severity: 'low' as AlertSeverity, color: '#5A5E72', icon: Info },
        ]).map((item) => (
          <button
            key={item.severity}
            onClick={() => setSeverityFilter(severityFilter === item.severity ? '' : item.severity)}
            className={`rounded-card border p-4 text-left transition-all hover:-translate-y-0.5 ${
              severityFilter === item.severity
                ? 'border-vs-accent-blue bg-sg-surface-dim'
                : 'border-sg-border-subtle bg-white'
            }`}
          >
            <div className="flex items-center justify-between">
              <item.icon className="h-5 w-5" style={{ color: item.color }} />
              <span className="text-2xl font-bold text-sg-text-primary">
                <CountUp end={summary?.by_severity[item.severity] || 0} duration={1} />
              </span>
            </div>
            <p className="mt-1 text-xs text-sg-text-secondary">{item.label}</p>
          </button>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="mt-6 flex items-center gap-2 border-b border-sg-border-subtle pb-0">
        {(['all', 'open', 'acknowledged', 'resolved'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => { setStatusFilter(tab === 'all' ? '' : tab); setPage(1); }}
            className={`border-b-2 px-4 py-2.5 text-sm font-medium capitalize transition-all ${
              (tab === 'all' && !statusFilter) || statusFilter === tab
                ? 'border-vs-accent-blue text-sg-text-primary'
                : 'border-transparent text-sg-text-secondary hover:text-sg-text-secondary'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="mt-4 space-y-3">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 rounded-card border border-sg-border-subtle bg-white">
              <div className="skeleton-shimmer h-full w-full rounded-lg" />
            </div>
          ))
        ) : data?.alerts.length === 0 ? (
          <div className="flex flex-col items-center py-16">
            <CheckCircle2 className="h-12 w-12 text-sg-risk-green" />
            <p className="mt-4 text-lg font-medium text-sg-text-secondary">All caught up!</p>
            <p className="text-sm text-sg-text-secondary">No alerts match your filters.</p>
          </div>
        ) : (
          data?.alerts.map((alert, i) => (
            <AlertCard key={alert.id} alert={alert} index={i} />
          ))
        )}
      </div>

      {/* Pagination */}
      {data?.pagination && data.pagination.total_pages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-button border border-sg-border-subtle bg-white px-4 py-2 text-sm text-sg-text-secondary disabled:opacity-30"
          >
            Previous
          </button>
          <span className="text-sm text-sg-text-secondary">
            Page {page} of {data.pagination.total_pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pagination.total_pages, p + 1))}
            disabled={page === data.pagination.total_pages}
            className="rounded-button border border-sg-border-subtle bg-white px-4 py-2 text-sm text-sg-text-secondary disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
