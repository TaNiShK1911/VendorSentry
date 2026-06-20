import { useQuery } from '@tanstack/react-query';
import { evaluationApi } from '@/api';
import {
  Target, Crosshair, Eye, BrainCircuit, Loader2,
} from 'lucide-react';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend,
} from 'recharts';

// ---- Custom Tooltip ----
function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color?: string }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-sg-border-subtle bg-sg-surface p-3 shadow-lg">
      <p className="mb-1 text-xs text-sg-text-secondary">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-xs text-sg-text-secondary">{entry.name}: {(entry.value * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

// ---- Metric Card ----
function MetricCard({ label, value, icon: Icon, color, delay }: {
  label: string; value: number; icon: React.ElementType; color: string; delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="rounded-card border border-sg-border-subtle bg-sg-surface p-5 shadow-card"
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
          {label}
        </span>
        <Icon className="h-5 w-5" style={{ color }} />
      </div>
      <div className="mt-3">
        <CountUp end={value * 100} duration={2} decimals={1} suffix="%" className="text-[28px] font-bold text-sg-text-primary" />
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-sg-surface/[0.06]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 1.5, delay: delay + 0.3 }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
    </motion.div>
  );
}

// ============================================================
// Evaluation Page
// ============================================================

export default function EvaluationPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['evaluation', 'metrics'],
    queryFn: () => evaluationApi.getMetrics(),
  });

  if (isLoading || !data) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-sg-primary" />
      </div>
    );
  }

  // Severity tier bar chart data (available for future chart use)

  // Score distribution data
  const scoreDistData = data.score_distribution.bins.map((bin, i) => ({
    bin,
    Predicted: data.score_distribution.predicted[i],
    Actual: data.score_distribution.actual[i],
  }));

  // Confusion matrix data for heatmap
  const confusionData = data.confusion_matrix;

  const maxConfusion = Math.max(...confusionData.matrix.flat());

  return (
    <div className="p-8">
      <h1 className="text-3xl font-semibold tracking-tight text-sg-text-primary">Evaluation Metrics</h1>
      <p className="mt-1 text-sm text-sg-text-secondary">
        AI scoring accuracy assessment across severity tiers.
      </p>

      {/* Metric cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Overall Accuracy" value={data.overall_metrics.accuracy} icon={Target} color="#365DE5" delay={0} />
        <MetricCard label="Precision" value={data.overall_metrics.precision} icon={Crosshair} color="#1DB954" delay={0.05} />
        <MetricCard label="Recall" value={data.overall_metrics.recall} icon={Eye} color="#E8A838" delay={0.1} />
        <MetricCard label="F1 Score" value={data.overall_metrics.f1_score} icon={BrainCircuit} color="#7C5CFC" delay={0.15} />
      </div>

      {/* Charts */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Score Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-card border border-sg-border-subtle bg-sg-surface p-5 shadow-card"
        >
          <h3 className="text-base font-semibold text-sg-text-primary">Score Distribution</h3>
          <div className="mt-4">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={scoreDistData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--sg-border-subtle)" />
                <XAxis dataKey="bin" tick={{ fill: 'var(--sg-text-secondary)', fontSize: 10 }} axisLine={{ stroke: 'var(--sg-border)' }} />
                <YAxis tick={{ fill: 'var(--sg-text-secondary)', fontSize: 11 }} axisLine={{ stroke: 'var(--sg-border)' }} />
                <Tooltip content={<ChartTooltip />} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="Predicted" fill="#365DE5" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Actual" fill="#1DB954" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Confusion Matrix */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-card border border-sg-border-subtle bg-sg-surface p-5 shadow-card"
        >
          <h3 className="text-base font-semibold text-sg-text-primary">Confusion Matrix</h3>
          <div className="mt-4">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="p-2" />
                    {confusionData.predicted.map((p) => (
                      <th key={p} className="p-2 text-center text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                        Pred: {p}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {confusionData.matrix.map((row, i) => (
                    <tr key={i}>
                      <td className="p-2 text-[10px] font-semibold uppercase text-sg-text-secondary">
                        {confusionData.actual[i]}
                      </td>
                      {row.map((val, j) => {
                        const intensity = val / maxConfusion;
                        return (
                          <td key={j} className="p-1">
                            <div
                              className="flex h-10 items-center justify-center rounded text-sm font-bold text-sg-text-primary"
                              style={{
                                backgroundColor: `rgba(54, 93, 229, ${0.1 + intensity * 0.5})`,
                              }}
                            >
                              {val}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      </div>

      {/* By Severity Tier */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="mt-6 rounded-card border border-sg-border-subtle bg-sg-surface p-5 shadow-card"
      >
        <h3 className="text-base font-semibold text-sg-text-primary">Metrics by Severity Tier</h3>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-sg-border-subtle">
                <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Tier</th>
                <th className="pb-2 text-right text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Accuracy</th>
                <th className="pb-2 text-right text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Precision</th>
                <th className="pb-2 text-right text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Recall</th>
                <th className="pb-2 text-right text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">F1</th>
                <th className="pb-2 text-right text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">Samples</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.by_severity_tier).map(([tier, metrics]) => (
                <tr key={tier} className="border-b border-white/[0.03]">
                  <td className="py-3">
                    <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                      tier === 'CRITICAL' ? 'tier-badge-critical'
                      : tier === 'HIGH' ? 'tier-badge-high'
                      : tier === 'MEDIUM' ? 'tier-badge-medium'
                      : tier === 'LOW' ? 'tier-badge-low'
                      : 'tier-badge-clear'
                    }`}>
                      {tier}
                    </span>
                  </td>
                  <td className="py-3 text-right text-sm text-sg-text-primary">{(metrics.accuracy * 100).toFixed(1)}%</td>
                  <td className="py-3 text-right text-sm text-sg-text-primary">{(metrics.precision * 100).toFixed(1)}%</td>
                  <td className="py-3 text-right text-sm text-sg-text-primary">{(metrics.recall * 100).toFixed(1)}%</td>
                  <td className="py-3 text-right text-sm text-sg-text-primary">{(metrics.f1_score * 100).toFixed(1)}%</td>
                  <td className="py-3 text-right text-sm text-sg-text-secondary">{metrics.sample_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Dataset Info */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-6 rounded-card border border-sg-border-subtle bg-sg-surface p-5 shadow-card"
      >
        <h3 className="text-base font-semibold text-sg-text-primary">Dataset Information</h3>
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Total Evaluated</p>
            <p className="mt-1 text-lg font-semibold text-sg-text-primary">{data.dataset_info.total_vendors_evaluated}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Ground Truth</p>
            <p className="mt-1 text-lg font-semibold text-sg-text-primary">{data.dataset_info.ground_truth_available}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Period</p>
            <p className="mt-1 text-sm text-sg-text-secondary">{data.dataset_info.evaluation_period}</p>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">MAE</p>
            <p className="mt-0.5 text-sm font-medium text-sg-text-primary">{data.overall_metrics.mae}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">RMSE</p>
            <p className="mt-0.5 text-sm font-medium text-sg-text-primary">{data.overall_metrics.rmse}</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
