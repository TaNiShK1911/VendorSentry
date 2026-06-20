import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { reportsApi, vendorsApi } from '@/api';
import { FileText, BarChart3, Loader2, Download } from 'lucide-react';
import { motion } from 'framer-motion';
import { marked } from 'marked';
import html2pdf from 'html2pdf.js';

export default function ReportsPage() {
  const [selectedVendor, setSelectedVendor] = useState('');
  const [generating, setGenerating] = useState<'vendor' | 'portfolio' | null>(null);

  const { data: vendors } = useQuery({
    queryKey: ['vendors', 'list', { per_page: 100 }],
    queryFn: () => vendorsApi.list({ per_page: 100 }),
  });

  const handleVendorReport = async () => {
    if (!selectedVendor) return;
    setGenerating('vendor');
    try {
      const markdownText = await reportsApi.getVendorReport(selectedVendor, 'markdown') as string;
      
      const element = document.createElement('div');
      // Set explicit black text and white background for PDF rendering
      element.innerHTML = `<div style="font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; color: black; background: white;">
        ${await marked.parse(markdownText)}
      </div>`;
      
      const opt = {
        margin:       0.5,
        filename:     `vendor_report_${selectedVendor}_${new Date().toISOString().split('T')[0]}.pdf`,
        image:        { type: 'jpeg' as const, quality: 0.98 },
        html2canvas:  { scale: 2 },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' as const }
      };

      await html2pdf().set(opt).from(element).save();
    } catch (e) {
      console.error("Failed to generate report", e);
    }
    setGenerating(null);
  };

  const handlePortfolioReport = async () => {
    setGenerating('portfolio');
    try {
      const markdownText = await reportsApi.getPortfolioReport('markdown') as string;
      
      const element = document.createElement('div');
      element.innerHTML = `<div style="font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; color: black; background: white;">
        ${await marked.parse(markdownText)}
      </div>`;
      
      const opt = {
        margin:       0.5,
        filename:     `portfolio_report_${new Date().toISOString().split('T')[0]}.pdf`,
        image:        { type: 'jpeg' as const, quality: 0.98 },
        html2canvas:  { scale: 2 },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' as const }
      };

      await html2pdf().set(opt).from(element).save();
    } catch (e) {
      console.error("Failed to generate portfolio report", e);
    }
    setGenerating(null);
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-semibold tracking-tight text-sg-text-primary">Reports</h1>
      <p className="mt-1 text-sm text-sg-text-secondary">
        Generate detailed risk reports for vendors or your entire portfolio.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Vendor Report Card */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0 }}
          className="rounded-card border border-sg-border-subtle bg-sg-surface p-8 shadow-card"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-sg-surface-dim">
            <FileText className="h-7 w-7 text-sg-primary" />
          </div>
          <h2 className="mt-5 text-xl font-semibold text-sg-text-primary">Vendor Report</h2>
          <p className="mt-1 text-sm text-sg-text-secondary">
            Generate a detailed risk report for a specific vendor in PDF format.
          </p>

          <div className="mt-5">
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
              Select Vendor
            </label>
            <select
              value={selectedVendor}
              onChange={(e) => setSelectedVendor(e.target.value)}
              className="w-full rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-3 text-sm text-sg-text-primary outline-none transition-all focus:border-vs-accent-blue"
            >
              <option value="">Choose a vendor...</option>
              {vendors?.vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleVendorReport}
            disabled={!selectedVendor || generating === 'vendor'}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-button bg-sg-primary py-3 text-sm font-semibold text-sg-text-primary transition-all hover:bg-sg-primary-hover disabled:opacity-50"
          >
            {generating === 'vendor' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Generate PDF
          </button>
        </motion.div>

        {/* Portfolio Report Card */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-card border border-sg-border-subtle bg-sg-surface p-8 shadow-card"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-sg-surface-dim">
            <BarChart3 className="h-7 w-7 text-sg-primary" />
          </div>
          <h2 className="mt-5 text-xl font-semibold text-sg-text-primary">Portfolio Report</h2>
          <p className="mt-1 text-sm text-sg-text-secondary">
            Generate a comprehensive portfolio-level risk report in PDF format.
          </p>

          <div className="mt-5 rounded-lg bg-sg-surface-muted border border-sg-border-subtle p-4">
            <p className="text-sm text-sg-text-secondary">This report includes:</p>
            <ul className="mt-2 space-y-1 text-sm text-sg-text-secondary">
              <li>• Portfolio risk distribution</li>
              <li>• Top risk vendors summary</li>
              <li>• Alert summary and trends</li>
              <li>• Compliance overview</li>
            </ul>
          </div>

          <button
            onClick={handlePortfolioReport}
            disabled={generating === 'portfolio'}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-button bg-sg-primary py-3 text-sm font-semibold text-sg-text-primary transition-all hover:bg-sg-primary-hover disabled:opacity-50"
          >
            {generating === 'portfolio' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Generate PDF
          </button>
        </motion.div>
      </div>
    </div>
  );
}
