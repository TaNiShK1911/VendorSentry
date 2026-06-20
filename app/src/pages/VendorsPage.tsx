import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { vendorsApi } from '@/api';
import { useAuth } from '@/hooks/useAuth';
import {
  Search, Filter, Download, Plus, ChevronLeft, ChevronRight, X,
} from 'lucide-react';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';
import {
  VENDOR_SORT_OPTIONS, VENDOR_TYPES, RISK_TIERS,
} from '@/types';
import type { Vendor, VendorFilters, RiskTier } from '@/types';
import { VendorFormDialog } from '@/components/vendors/VendorFormDialog';

// ---- Vendor Card Component ----
function VendorCard({ vendor, index }: { vendor: Vendor; index: number }) {
  const navigate = useNavigate();

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#F85151';
    if (score >= 40) return '#E8A838';
    return '#1DB954';
  };

  const getTierBadge = (tier: RiskTier) => {
    switch (tier) {
      case 'CRITICAL': return 'tier-badge-critical';
      case 'HIGH': return 'tier-badge-high';
      case 'MEDIUM': return 'tier-badge-medium';
      case 'LOW': return 'tier-badge-low';
      case 'CLEAR': return 'tier-badge-clear';
    }
  };

  const getStatusDot = (color: string) => {
    switch (color) {
      case 'RED': return 'bg-[#F85151]';
      case 'YELLOW': return 'bg-[#E8A838]';
      case 'GREEN': return 'bg-[#1DB954]';
      default: return 'bg-[#1DB954]';
    }
  };

  const scoreColor = getScoreColor(vendor.composite_score);
  const circumference = 2 * Math.PI * 20;
  const strokeDashoffset = circumference - (vendor.composite_score / 100) * circumference;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      onClick={() => navigate(`/vendors/${vendor.id}`)}
      className="cursor-pointer rounded-card border border-sg-border-subtle bg-sg-surface p-5 shadow-card transition-all hover:-translate-y-0.5 hover:border-sg-border-focus hover:shadow-lift"
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-display text-base font-bold text-sg-text-primary">{vendor.name}</h3>
            <span className={`h-2.5 w-2.5 rounded-full ${getStatusDot(vendor.status_color)}`} />
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="rounded bg-sg-surface-muted px-2 py-0.5 text-[10px] font-medium text-sg-text-secondary border border-sg-border-subtle">
              {vendor.vendor_type}
            </span>
            <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${getTierBadge(vendor.risk_tier)}`}>
              {vendor.risk_tier}
            </span>
          </div>
        </div>

        {/* Score circle */}
        <div className="relative flex h-14 w-14 items-center justify-center">
          <svg className="h-14 w-14 -rotate-90" viewBox="0 0 48 48">
            <circle cx="24" cy="24" r="20" fill="none" stroke="#e2e2e2" strokeWidth="3" />
            <circle
              cx="24" cy="24" r="20" fill="none"
              stroke={scoreColor}
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-1000"
            />
          </svg>
          <span className="absolute text-sm font-bold" style={{ color: scoreColor }}>
            {vendor.composite_score}
          </span>
        </div>
      </div>

      {/* Info grid */}
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">PII Access</p>
          <p className={`mt-0.5 text-sm font-medium ${vendor.has_pii_access ? 'text-sg-risk-yellow' : 'text-sg-text-secondary'}`}>
            {vendor.has_pii_access ? 'Yes' : 'No'}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Active Alerts</p>
          <p className={`mt-0.5 text-sm font-medium ${vendor.active_alerts > 0 ? 'text-sg-risk-red' : 'text-sg-text-secondary'}`}>
            {vendor.active_alerts}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Contract End</p>
          <p className="mt-0.5 text-sm text-sg-text-secondary">
            {vendor.contract_end ? new Date(vendor.contract_end).toLocaleDateString() : 'N/A'}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Last Assessed</p>
          <p className="mt-0.5 text-sm text-sg-text-secondary">
            {vendor.last_assessed ? new Date(vendor.last_assessed).toLocaleDateString() : 'Never'}
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between border-t border-sg-border-subtle pt-3">
        <span className="text-xs text-sg-text-secondary">Click for details</span>
        <span className="text-xs font-medium text-sg-text-primary">View Details &rarr;</span>
      </div>
    </motion.div>
  );
}

// ============================================================
// Vendors Page
// ============================================================

export default function VendorsPage() {
  const { canEdit } = useAuth();
  const [showFilters, setShowFilters] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  // Filter state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedTiers, setSelectedTiers] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState('');
  const [scoreMin, setScoreMin] = useState('');
  const [scoreMax, setScoreMax] = useState('');
  const [hasPii, setHasPii] = useState(false);
  const [sort, setSort] = useState('score_desc');
  const [page, setPage] = useState(1);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Build filters
  const filters: VendorFilters & { page: number; per_page: number; sort: string } = {
    page,
    per_page: 12,
    sort,
    ...(debouncedSearch && { search: debouncedSearch }),
    ...(selectedTiers.length > 0 && { tier: selectedTiers.join(',') }),
    ...(selectedType && { type: selectedType }),
    ...(scoreMin && { score_min: Number(scoreMin) }),
    ...(scoreMax && { score_max: Number(scoreMax) }),
    ...(hasPii && { has_pii: true }),
  };

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['vendors', 'list', filters],
    queryFn: () => vendorsApi.list(filters),
  });

  const handleExport = useCallback(async () => {
    try {
      const blob = await vendorsApi.exportCsv({
        ...(debouncedSearch && { search: debouncedSearch }),
        ...(selectedTiers.length > 0 && { tier: selectedTiers.join(',') }),
        ...(selectedType && { type: selectedType }),
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vendors_export_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      // Handle error
    }
  }, [debouncedSearch, selectedTiers, selectedType]);

  const toggleTier = (tier: string) => {
    setSelectedTiers((prev) =>
      prev.includes(tier) ? prev.filter((t) => t !== tier) : [...prev, tier]
    );
    setPage(1);
  };

  const clearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setSelectedTiers([]);
    setSelectedType('');
    setScoreMin('');
    setScoreMax('');
    setHasPii(false);
    setPage(1);
  };

  const hasActiveFilters = debouncedSearch || selectedTiers.length > 0 || selectedType || scoreMin || scoreMax || hasPii;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-3xl font-bold uppercase tracking-tight text-sg-text-primary">Vendors</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 rounded-button border px-4 py-2.5 text-sm font-medium transition-all ${
              showFilters || hasActiveFilters
                ? 'border-sg-primary bg-sg-surface-muted text-sg-primary'
                : 'border-sg-border-subtle bg-sg-surface text-sg-text-secondary hover:text-sg-text-primary hover:border-sg-border-focus'
            }`}
          >
            <Filter className="h-4 w-4" />
            Filters
            {hasActiveFilters && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-sg-primary text-[10px] font-bold text-white">
                {[debouncedSearch, ...selectedTiers, selectedType, scoreMin, scoreMax, hasPii].filter(Boolean).length}
              </span>
            )}
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 rounded-button border border-sg-border-subtle bg-sg-surface px-4 py-2.5 text-sm font-medium text-sg-text-secondary transition-all hover:text-sg-text-primary hover:border-sg-border-focus"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
          {canEdit && (
            <button
              onClick={() => setCreateOpen(true)}
              className="flex items-center gap-2 rounded-button bg-sg-primary px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-sg-primary-hover hover:-translate-y-0.5"
            >
              <Plus className="h-4 w-4" />
              Add Vendor
            </button>
          )}
        </div>
      </div>

      {/* Filter bar */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-4 rounded-card border border-sg-border-subtle bg-sg-surface p-4"
        >
          <div className="flex flex-wrap items-end gap-4">
            {/* Search */}
            <div className="min-w-[240px] flex-1">
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-sg-text-secondary" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  placeholder="Search vendors..."
                  className="w-full rounded-input border border-sg-border-subtle bg-sg-surface py-2.5 pl-10 pr-4 text-sm text-sg-text-primary placeholder-sg-text-secondary outline-none transition-all focus:border-sg-border-focus"
                />
              </div>
            </div>

            {/* Tier filter */}
            <div>
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                Tier
              </label>
              <div className="flex gap-1.5">
                {RISK_TIERS.map((tier) => (
                  <button
                    key={tier}
                    onClick={() => toggleTier(tier)}
                    className={`rounded px-2.5 py-1.5 text-[10px] font-semibold uppercase transition-all ${
                      selectedTiers.includes(tier)
                        ? tier === 'CRITICAL' ? 'bg-sg-risk-red-bg text-sg-risk-red ring-1 ring-vs-risk-red/30'
                        : tier === 'HIGH' ? 'bg-sg-risk-yellow-bg text-sg-risk-yellow ring-1 ring-vs-risk-yellow/30'
                        : tier === 'MEDIUM' ? 'bg-sg-surface-dim text-sg-text-primary ring-1 ring-vs-accent-blue/30'
                        : tier === 'LOW' ? 'bg-sg-risk-green-bg text-sg-risk-green ring-1 ring-vs-risk-green/30'
                        : 'bg-sg-risk-clear-bg text-sg-risk-clear ring-1 ring-sg-risk-clear/30'
                        : 'bg-sg-surface border border-sg-border-subtle text-sg-text-secondary hover:text-sg-text-primary'
                    }`}
                  >
                    {tier}
                  </button>
                ))}
              </div>
            </div>

            {/* Type filter */}
            <div className="min-w-[160px]">
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                Type
              </label>
              <select
                value={selectedType}
                onChange={(e) => { setSelectedType(e.target.value); setPage(1); }}
                className="w-full rounded-input border border-sg-border-subtle bg-sg-surface px-3 py-2.5 text-sm text-sg-text-primary outline-none transition-all focus:border-sg-border-focus"
              >
                <option value="">All Types</option>
                {VENDOR_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {/* Score range */}
            <div className="flex gap-2">
              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                  Min Score
                </label>
                <input
                  type="number"
                  value={scoreMin}
                  onChange={(e) => { setScoreMin(e.target.value); setPage(1); }}
                  placeholder="0"
                  min={0}
                  max={100}
                  className="w-20 rounded-input border border-sg-border-subtle bg-sg-surface px-3 py-2.5 text-sm text-sg-text-primary placeholder-sg-text-secondary outline-none transition-all focus:border-sg-border-focus"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                  Max Score
                </label>
                <input
                  type="number"
                  value={scoreMax}
                  onChange={(e) => { setScoreMax(e.target.value); setPage(1); }}
                  placeholder="100"
                  min={0}
                  max={100}
                  className="w-20 rounded-input border border-sg-border-subtle bg-sg-surface px-3 py-2.5 text-sm text-sg-text-primary placeholder-sg-text-secondary outline-none transition-all focus:border-sg-border-focus"
                />
              </div>
            </div>

            {/* PII toggle */}
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={hasPii}
                onChange={(e) => { setHasPii(e.target.checked); setPage(1); }}
                className="h-4 w-4 rounded border-sg-border-subtle bg-sg-surface accent-sg-primary"
              />
              <span className="text-sm text-sg-text-secondary">Has PII Access</span>
            </label>

            {/* Sort */}
            <div className="min-w-[160px]">
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                Sort
              </label>
              <select
                value={sort}
                onChange={(e) => { setSort(e.target.value); setPage(1); }}
                className="w-full rounded-input border border-sg-border-subtle bg-sg-surface px-3 py-2.5 text-sm text-sg-text-primary outline-none transition-all focus:border-sg-border-focus"
              >
                {VENDOR_SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Clear */}
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="flex items-center gap-1 rounded-button border border-sg-border-subtle px-3 py-2.5 text-sm text-sg-text-secondary transition-all hover:text-sg-text-primary"
              >
                <X className="h-3.5 w-3.5" />
                Clear
              </button>
            )}
          </div>
        </motion.div>
      )}

      {/* Results count */}
      <div className="mt-4 text-sm text-sg-text-secondary">
        {data?.pagination && (
          <span>
            Showing <CountUp end={data.vendors.length} duration={0.5} /> of{' '}
            <CountUp end={data.pagination.total} duration={0.5} /> vendors
          </span>
        )}
      </div>

      {/* Vendor cards grid */}
      {isLoading ? (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-[260px] rounded-card border border-sg-border-subtle bg-sg-surface p-5">
              <div className="skeleton-shimmer h-full w-full rounded-lg" />
            </div>
          ))}
        </div>
      ) : data?.vendors.length === 0 ? (
        <div className="mt-8 flex flex-col items-center justify-center py-16">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-sg-surface">
            <Search className="h-8 w-8 text-sg-text-secondary" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-sg-text-secondary">No vendors found</h3>
          <p className="mt-1 text-sm text-sg-text-secondary">
            Try adjusting your filters or add a new vendor.
          </p>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.vendors.map((vendor, i) => (
            <VendorCard key={vendor.id} vendor={vendor} index={i} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data?.pagination && data.pagination.total_pages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="flex items-center gap-1 rounded-button border border-sg-border-subtle bg-sg-surface px-4 py-2 text-sm font-semibold text-sg-text-secondary transition-all hover:text-sg-text-primary hover:border-sg-border-focus disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </button>
          <span className="text-sm text-sg-text-secondary">
            Page {page} of {data.pagination.total_pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pagination.total_pages, p + 1))}
            disabled={page === data.pagination.total_pages}
            className="flex items-center gap-1 rounded-button border border-sg-border-subtle bg-sg-surface px-4 py-2 text-sm font-semibold text-sg-text-secondary transition-all hover:text-sg-text-primary hover:border-sg-border-focus disabled:opacity-30"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Create vendor dialog */}
      <VendorFormDialog open={createOpen} onOpenChange={setCreateOpen} onSuccess={refetch} />
    </div>
  );
}
