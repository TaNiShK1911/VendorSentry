import { useQuery } from '@tanstack/react-query';
import { scoringApi, alertsApi, vendorsApi } from '@/api';
import {
  Users, AlertTriangle, AlertOctagon, Bell, TrendingUp, ArrowRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';
import {
  PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';

// ---- Animated Number Component ----
function AnimatedNumber({ value, duration = 2 }: { value: number; duration?: number }) {
  return (
    <CountUp
      end={value}
      duration={duration}
      separator=","
      className="text-[28px] font-bold text-sg-text-primary"
    />
  );
}

// ---- Custom Tooltip for Charts ----
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color?: string; fill?: string; stroke?: string }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-sg-border-subtle bg-sg-surface p-3 shadow-lg">
      <p className="mb-1 text-xs text-sg-text-secondary">{label}</p>
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: entry.color || entry.fill || entry.stroke }}
            />
            <span className="text-xs text-sg-text-secondary">{entry.name}:</span>
            <span className="text-sm font-medium text-sg-text-primary">{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Hero Metric Card ----
function MetricCard({
  label, value, icon: Icon, color, trend, delay = 0,
}: {
  label: string; value: number; icon: React.ElementType; color: string;
  trend?: string; delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="rounded-card border border-sg-border-subtle bg-white p-4 shadow-card transition-all hover:-translate-y-0.5 hover:border-sg-border-focus hover:shadow-lift"
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
          {label}
        </span>
        <Icon className="h-5 w-5" style={{ color }} />
      </div>
      <div className="mt-3">
        <AnimatedNumber value={value} />
      </div>
      {trend && (
        <div className="mt-2 flex items-center gap-1 text-sm text-sg-risk-green">
          <TrendingUp className="h-3.5 w-3.5" />
          <span>{trend}</span>
        </div>
      )}
    </motion.div>
  );
}

// ---- Risk Distribution Donut Chart ----
function RiskDistributionChart({ data }: { data: { name: string; value: number; color: string }[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
      className="rounded-card border border-sg-border-subtle bg-white p-5 shadow-card"
    >
      <h3 className="font-display text-base font-bold uppercase tracking-wider text-sg-text-primary">Risk Distribution</h3>
      <div className="mt-4">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={3}
              dataKey="value"
              animationBegin={0}
              animationDuration={800}
              animationEasing="ease-out"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            {/* Center label */}
            <text x="50%" y="45%" textAnchor="middle" fill="#1a1c1c" fontSize={24} fontWeight={600}>
              {total}
            </text>
            <text x="50%" y="58%" textAnchor="middle" fill="#5A5E72" fontSize={12}>
              vendors
            </text>
          </PieChart>
        </ResponsiveContainer>
      </div>
      {/* Legend */}
      <div className="mt-2 flex items-center justify-center gap-6">
        {data.map((entry) => (
          <div key={entry.name} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-xs text-sg-text-secondary">{entry.name}</span>
            <span className="text-xs font-semibold text-sg-text-primary">{entry.value}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ---- Portfolio Trend Line Chart ----
function PortfolioTrendChart({ data }: { data: Array<{ date: string; avgScore: number; riskVendors: number }> }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.4 }}
      className="rounded-card border border-sg-border-subtle bg-white p-5 shadow-card"
    >
      <h3 className="font-display text-base font-bold uppercase tracking-wider text-sg-text-primary">Portfolio Risk Trend (90 Days)</h3>
      <div className="mt-4">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e2e2" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#5A5E72', fontSize: 11 }}
              axisLine={{ stroke: '#BDBDBD' }}
              tickFormatter={(value) => {
                const d = new Date(value);
                return `${d.toLocaleString('en', { month: 'short' })} ${d.getDate()}`;
              }}
            />
            <YAxis
              tick={{ fill: '#5A5E72', fontSize: 11 }}
              axisLine={{ stroke: '#BDBDBD' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="avgScore"
              name="Average Score"
              stroke="#1a1c1c"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, fill: '#1a1c1c' }}
              animationDuration={1000}
            />
            <Line
              type="monotone"
              dataKey="riskVendors"
              name="Risk Vendors (>70)"
              stroke="#bb0507"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, fill: '#bb0507' }}
              animationDuration={1000}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

// ---- Top Risk Vendors Table ----
function TopRiskVendorsTable({ vendors }: { vendors: Array<{ id: string; name: string; vendor_type: string; status_color: string; risk_tier: string; composite_score: number; active_alerts: number; last_assessed: string | null }> }) {
  const navigate = useNavigate();

  const getStatusDot = (color: string) => {
    switch (color) {
      case 'RED': return 'status-dot-red';
      case 'YELLOW': return 'status-dot-yellow';
      case 'GREEN': return 'status-dot-green';
      default: return 'status-dot-green';
    }
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

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#F85151';
    if (score >= 40) return '#E8A838';
    return '#1DB954';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.35 }}
      className="rounded-card border border-sg-border-subtle bg-white p-5 shadow-card"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-display text-base font-bold uppercase tracking-wider text-sg-text-primary">Highest Risk Vendors</h3>
        <button
          onClick={() => navigate('/vendors')}
          className="flex items-center gap-1 text-xs font-semibold text-sg-primary hover:underline"
        >
          View All <ArrowRight className="h-3 w-3" />
        </button>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-sg-border-subtle">
              <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Vendor</th>
              <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Status</th>
              <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Tier</th>
              <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Score</th>
              <th className="pb-2 text-right text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Alerts</th>
            </tr>
          </thead>
          <tbody>
            {vendors.map((vendor, i) => (
              <tr
                key={vendor.id}
                onClick={() => navigate(`/vendors/${vendor.id}`)}
                className="cursor-pointer border-b border-sg-border-subtle transition-colors hover:bg-sg-surface-muted"
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <td className="py-3">
                  <div>
                    <div className="text-sm font-medium text-sg-text-primary">{vendor.name}</div>
                    <div className="text-xs text-sg-text-secondary">{vendor.vendor_type}</div>
                  </div>
                </td>
                <td className="py-3">
                  <span className={`status-dot ${getStatusDot(vendor.status_color)}`} />
                </td>
                <td className="py-3">
                  <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${getTierBadge(vendor.risk_tier)}`}>
                    {vendor.risk_tier}
                  </span>
                </td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium" style={{ color: getScoreColor(vendor.composite_score) }}>
                      {vendor.composite_score}
                    </span>
                    <div className="h-1 w-[60px] overflow-hidden rounded-full bg-sg-border-subtle">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${vendor.composite_score}%`,
                          backgroundColor: getScoreColor(vendor.composite_score),
                        }}
                      />
                    </div>
                  </div>
                </td>
                <td className="py-3 text-right">
                  {vendor.active_alerts > 0 ? (
                    <span className="inline-flex items-center rounded-full bg-sg-risk-red-bg px-2 py-0.5 text-xs font-medium text-sg-risk-red">
                      {vendor.active_alerts}
                    </span>
                  ) : (
                    <span className="text-xs text-sg-text-secondary">0</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

// ============================================================
// Dashboard Page
// ============================================================

export default function DashboardPage() {
  // Polling queries — refetch every 5 seconds
  const { data: distribution } = useQuery({
    queryKey: ['portfolio', 'distribution'],
    queryFn: () => scoringApi.getScoreDistribution(),
    refetchInterval: 5000,
  });

  const { data: alertSummary } = useQuery({
    queryKey: ['alerts', 'summary'],
    queryFn: () => alertsApi.getSummary(),
    refetchInterval: 5000,
  });

  const { data: trend } = useQuery({
    queryKey: ['portfolio', 'trend', { range: '90d' }],
    queryFn: () => scoringApi.getScoreTrend('90d'),
  });

  const { data: topVendors } = useQuery({
    queryKey: ['vendors', 'list', { page: 1, sort: 'score_desc', per_page: 8 }],
    queryFn: () => vendorsApi.list({ page: 1, per_page: 8, sort: 'score_desc' }),
  });

  // Prepare donut chart data
  const donutData = distribution
    ? [
        { name: 'HIGH', value: distribution.by_status_color.RED, color: '#F85151' },
        { name: 'MEDIUM', value: distribution.by_status_color.YELLOW, color: '#E8A838' },
        { name: 'LOW', value: distribution.by_status_color.GREEN, color: '#1DB954' },
      ]
    : [];

  // Prepare trend data
  const trendData = trend?.data_points.map((dp) => ({
    date: dp.date,
    avgScore: dp.avg_score,
    riskVendors: dp.risk_vendor_count,
  })) || [];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-3xl font-bold uppercase tracking-tight text-sg-text-primary">Dashboard</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-sg-text-secondary">
            {new Date().toLocaleDateString('en', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </span>
        </div>
      </div>

      {/* Hero metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total Vendors"
          value={distribution?.total_vendors || 0}
          icon={Users}
          color="#1a1c1c"
          trend="+12 this month"
          delay={0}
        />
        <MetricCard
          label="Open Critical Alerts"
          value={alertSummary?.by_severity.critical || 0}
          icon={AlertTriangle}
          color="#F85151"
          delay={0.05}
        />
        <MetricCard
          label="Open High Alerts"
          value={alertSummary?.by_severity.high || 0}
          icon={AlertOctagon}
          color="#E8A838"
          delay={0.1}
        />
        <MetricCard
          label="Total Open Alerts"
          value={alertSummary?.total_open || 0}
          icon={Bell}
          color="#9A9DB0"
          delay={0.15}
        />
      </div>

      {/* Charts + Table */}
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-5">
        {/* Left column - Charts */}
        <div className="flex flex-col gap-6 xl:col-span-3">
          <RiskDistributionChart data={donutData} />
          <PortfolioTrendChart data={trendData} />
        </div>

        {/* Right column - Risk table */}
        <div className="xl:col-span-2">
          {topVendors?.vendors && (
            <TopRiskVendorsTable vendors={topVendors.vendors} />
          )}
        </div>
      </div>
    </div>
  );
}
