import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { vendorsApi } from '@/api';
import { getErrorMessage } from '@/api';
import { X, Loader2 } from 'lucide-react';
import { VENDOR_TYPES } from '@/types';
import type { Vendor, VendorCreateRequest, VendorUpdateRequest } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';

interface VendorFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendor?: Vendor;
  onSuccess: () => void;
}

export function VendorFormDialog({ open, onOpenChange, vendor, onSuccess }: VendorFormDialogProps) {
  const [name, setName] = useState('');
  const [vendorType, setVendorType] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [annualSpend, setAnnualSpend] = useState('');
  const [contractStart, setContractStart] = useState('');
  const [contractEnd, setContractEnd] = useState('');
  const [hasPii, setHasPii] = useState(false);
  const [hasFinancial, setHasFinancial] = useState(false);
  const [systemsAccess, setSystemsAccess] = useState('');
  const [dataNotes, setDataNotes] = useState('');
  const [error, setError] = useState('');

  const isEditing = !!vendor;

  useEffect(() => {
    if (vendor) {
      setName(vendor.name);
      setVendorType(vendor.vendor_type);
      setContactEmail(vendor.contact_email);
      setAnnualSpend(vendor.annual_spend?.toString() || '');
      setContractStart(vendor.contract_start || '');
      setContractEnd(vendor.contract_end || '');
      setHasPii(vendor.has_pii_access);
      setHasFinancial(vendor.has_financial_access);
      setSystemsAccess(vendor.systems_access?.join(', ') || '');
      setDataNotes(vendor.data_access_notes || '');
    } else {
      setName('');
      setVendorType('');
      setContactEmail('');
      setAnnualSpend('');
      setContractStart('');
      setContractEnd('');
      setHasPii(false);
      setHasFinancial(false);
      setSystemsAccess('');
      setDataNotes('');
    }
    setError('');
  }, [vendor, open]);

  const createMutation = useMutation({
    mutationFn: (data: VendorCreateRequest) => vendorsApi.create(data),
    onSuccess: () => {
      onOpenChange(false);
      onSuccess();
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: (data: VendorUpdateRequest) => vendorsApi.update(vendor!.id, data),
    onSuccess: () => {
      onOpenChange(false);
      onSuccess();
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const data = {
      name,
      vendor_type: vendorType,
      contact_email: contactEmail,
      ...(annualSpend && { annual_spend: Number(annualSpend) }),
      ...(contractStart && { contract_start: contractStart }),
      ...(contractEnd && { contract_end: contractEnd }),
      has_pii_access: hasPii,
      has_financial_access: hasFinancial,
      ...(systemsAccess && { systems_access: systemsAccess.split(',').map((s) => s.trim()) }),
      ...(dataNotes && { data_access_notes: dataNotes }),
    };

    if (isEditing) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data as VendorCreateRequest);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => onOpenChange(false)}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2 }}
            className="relative z-10 w-full max-w-lg rounded-xl border border-sg-border-subtle bg-sg-surface shadow-lift"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-sg-border-subtle px-6 py-4">
              <h2 className="text-lg font-semibold text-sg-text-primary">
                {isEditing ? 'Edit Vendor' : 'Add Vendor'}
              </h2>
              <button
                onClick={() => onOpenChange(false)}
                className="rounded-lg p-1 text-sg-text-secondary transition-colors hover:bg-white/[0.04] hover:text-sg-text-primary"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto p-6">
              {error && (
                <div className="mb-4 rounded-lg border border-vs-risk-red/20 bg-sg-risk-red-bg px-4 py-3 text-sm text-sg-risk-red">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                {/* Name */}
                <div>
                  <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                    Vendor Name *
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-2.5 text-sm text-sg-text-primary placeholder-vs-text-tertiary outline-none transition-all focus:border-vs-accent-blue focus:shadow-glow-blue"
                    placeholder="e.g. Amazon Web Services"
                  />
                </div>

                {/* Type + Email */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                      Type *
                    </label>
                    <select
                      value={vendorType}
                      onChange={(e) => setVendorType(e.target.value)}
                      required
                      className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-3 py-2.5 text-sm text-sg-text-primary outline-none transition-all focus:border-vs-accent-blue"
                    >
                      <option value="">Select type</option>
                      {VENDOR_TYPES.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                      Contact Email *
                    </label>
                    <input
                      type="email"
                      value={contactEmail}
                      onChange={(e) => setContactEmail(e.target.value)}
                      required
                      className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-2.5 text-sm text-sg-text-primary placeholder-vs-text-tertiary outline-none transition-all focus:border-vs-accent-blue focus:shadow-glow-blue"
                      placeholder="security@company.com"
                    />
                  </div>
                </div>

                {/* Annual Spend */}
                <div>
                  <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                    Annual Spend ($)
                  </label>
                  <input
                    type="number"
                    value={annualSpend}
                    onChange={(e) => setAnnualSpend(e.target.value)}
                    className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-2.5 text-sm text-sg-text-primary placeholder-vs-text-tertiary outline-none transition-all focus:border-vs-accent-blue focus:shadow-glow-blue"
                    placeholder="500000"
                  />
                </div>

                {/* Contract dates */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                      Contract Start
                    </label>
                    <input
                      type="date"
                      value={contractStart}
                      onChange={(e) => setContractStart(e.target.value)}
                      className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-3 py-2.5 text-sm text-sg-text-primary outline-none transition-all focus:border-vs-accent-blue"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                      Contract End
                    </label>
                    <input
                      type="date"
                      value={contractEnd}
                      onChange={(e) => setContractEnd(e.target.value)}
                      className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-3 py-2.5 text-sm text-sg-text-primary outline-none transition-all focus:border-vs-accent-blue"
                    />
                  </div>
                </div>

                {/* Toggles */}
                <div className="flex gap-6">
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={hasPii}
                      onChange={(e) => setHasPii(e.target.checked)}
                      className="h-4 w-4 rounded border-sg-border-subtle accent-vs-accent-blue"
                    />
                    <span className="text-sm text-sg-text-secondary">Has PII Access</span>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={hasFinancial}
                      onChange={(e) => setHasFinancial(e.target.checked)}
                      className="h-4 w-4 rounded border-sg-border-subtle accent-vs-accent-blue"
                    />
                    <span className="text-sm text-sg-text-secondary">Has Financial Access</span>
                  </label>
                </div>

                {/* Systems Access */}
                <div>
                  <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                    Systems Access (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={systemsAccess}
                    onChange={(e) => setSystemsAccess(e.target.value)}
                    className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-2.5 text-sm text-sg-text-primary placeholder-vs-text-tertiary outline-none transition-all focus:border-vs-accent-blue focus:shadow-glow-blue"
                    placeholder="Production DB, S3 Buckets, Lambda"
                  />
                </div>

                {/* Data Access Notes */}
                <div>
                  <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                    Data Access Notes
                  </label>
                  <textarea
                    value={dataNotes}
                    onChange={(e) => setDataNotes(e.target.value)}
                    rows={3}
                    className="w-full resize-none rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-2.5 text-sm text-sg-text-primary placeholder-vs-text-tertiary outline-none transition-all focus:border-vs-accent-blue focus:shadow-glow-blue"
                    placeholder="Describe the vendor's data access scope..."
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => onOpenChange(false)}
                  className="rounded-button border border-sg-border-subtle bg-transparent px-4 py-2.5 text-sm font-medium text-sg-text-secondary transition-all hover:bg-white/[0.04] hover:text-sg-text-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isPending}
                  className="flex items-center gap-2 rounded-button bg-sg-primary px-6 py-2.5 text-sm font-semibold text-sg-text-primary transition-all hover:bg-sg-primary-hover disabled:opacity-50"
                >
                  {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  {isEditing ? 'Update Vendor' : 'Create Vendor'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
