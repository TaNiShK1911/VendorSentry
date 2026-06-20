import { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { extractionApi, vendorsApi } from '@/api';
import { getErrorMessage } from '@/api';
import {
  ArrowLeft, UploadCloud, FileText, Shield, ClipboardCheck,
  Loader2, CheckCircle2, XCircle, AlertTriangle,
} from 'lucide-react';
import { motion } from 'framer-motion';
import type { DocumentType, ExtractionConflict } from '@/types';

// ---- Neural Network Canvas Animation ----
// ---- Conflict Card ----
function ConflictCard({ conflict }: { conflict: ExtractionConflict }) {
  return (
    <div className="rounded-card border border-vs-risk-red/15 bg-sg-surface p-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm font-bold text-sg-text-primary">{conflict.field}</span>
        <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
          (conflict.severity || '').toLowerCase() === 'high' ? 'bg-sg-risk-red-bg text-sg-risk-red'
          : (conflict.severity || '').toLowerCase() === 'medium' ? 'bg-sg-risk-yellow-bg text-sg-risk-yellow'
          : 'bg-vs-text-tertiary/10 text-sg-text-secondary'
        }`}>
          {conflict.severity || 'MEDIUM'}
        </span>
      </div>
      <p className="mt-2 text-sm text-sg-text-secondary">{conflict.description || conflict.note || 'Conflict detected'}</p>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className="rounded border border-sg-border-subtle bg-sg-surface-muted p-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Expected</p>
          <p className="mt-1 font-mono text-xs text-sg-text-primary">
            {typeof (conflict.expected ?? conflict.actual_on_record) === 'object' ? JSON.stringify(conflict.expected ?? conflict.actual_on_record) : String(conflict.expected ?? conflict.actual_on_record ?? 'undefined')}
          </p>
        </div>
        <div className="rounded border border-sg-border-subtle bg-sg-surface-muted p-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Extracted</p>
          <p className="mt-1 font-mono text-xs text-sg-risk-red">
            {typeof (conflict.extracted ?? conflict.claimed) === 'object' ? JSON.stringify(conflict.extracted ?? conflict.claimed) : String(conflict.extracted ?? conflict.claimed ?? 'undefined')}
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Extraction Page
// ============================================================

export default function ExtractionPage() {
  const { id } = useParams<{ id: string }>();
  const vendorId = id!;
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocumentType>('contract');
  const [isDragging, setIsDragging] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: vendor } = useQuery({
    queryKey: ['vendors', 'detail', vendorId],
    queryFn: () => vendorsApi.getById(vendorId),
  });

  const extractMutation = useMutation({
    mutationFn: () => extractionApi.startExtraction(vendorId, file!, docType),
    onSuccess: (data) => {
      setJobId(data.job_id);
    },
  });

  const { data: jobStatus } = useQuery({
    queryKey: ['extraction', 'job', jobId],
    queryFn: () => extractionApi.getStatus(jobId!),
    refetchInterval: (query) => {
      const data = query?.state?.data;
      if (!data) return 2000;
      return data.status === 'completed' || data.status === 'failed' ? false : 2000;
    },
    enabled: !!jobId,
  });

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && (droppedFile.type === 'application/pdf' || droppedFile.type === 'text/plain')) {
      setFile(droppedFile);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) setFile(selected);
  };

  const handleSubmit = () => {
    if (!file) return;
    extractMutation.mutate();
  };

  const handleReset = () => {
    setFile(null);
    setJobId(null);
    extractMutation.reset();
  };

  const hasConflicts = jobStatus?.result?.conflicts && jobStatus.result.conflicts.length > 0;
  
  const isProcessing = jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'failed';
  const isCompleted = jobStatus && jobStatus.status === 'completed';
  const isFailed = jobStatus && jobStatus.status === 'failed';

  const docTypeOptions: { value: DocumentType; label: string; icon: React.ElementType }[] = [
    { value: 'contract', label: 'Contract', icon: FileText },
    { value: 'security_assessment', label: 'Security Assessment', icon: Shield },
    { value: 'audit_report', label: 'Audit Report', icon: ClipboardCheck },
  ];

  return (
    <div className="min-h-screen pb-12 pt-8">
      {/* Removed Neural Background */}

      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/vendors/${vendorId}`)}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-sg-border-subtle bg-white text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-sg-text-primary"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="font-display text-2xl font-bold uppercase tracking-wider text-sg-text-primary">Extract Vendor Document</h1>
            <p className="mt-1 text-sm text-sg-text-secondary">
              {vendor?.name ? `Uploading to ${vendor.name}` : 'Loading vendor...'}
            </p>
          </div>
        </div>

        {/* Upload + Results */}
        {!jobId && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-5"
          >
            {/* Upload Panel */}
            <div className="lg:col-span-2">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`cursor-pointer rounded-card border-2 border-dashed p-8 text-center transition-all ${
                  isDragging
                    ? 'border-sg-primary bg-sg-surface-muted'
                    : 'border-sg-border-subtle bg-white hover:border-sg-border-focus'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <UploadCloud className="mx-auto h-12 w-12 text-sg-text-secondary" />
                <p className="mt-4 text-lg font-medium text-sg-text-secondary">
                  {file ? file.name : 'Drop PDF or text file here'}
                </p>
                <p className="mt-1 text-sm text-sg-text-secondary">
                  {file ? `${(file.size / 1024).toFixed(1)} KB` : 'or click to browse'}
                </p>
              </div>

              {/* Document Type Selector */}
              <div className="mt-4">
                <label className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                  Document Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {docTypeOptions.map((opt) => {
                    const OptIcon = opt.icon;
                    return (
                      <button
                        key={opt.value}
                        onClick={() => setDocType(opt.value)}
                        className={`flex flex-col items-center gap-2 rounded-card border p-4 transition-all ${
                          docType === opt.value
                            ? 'border-sg-primary bg-sg-surface-muted text-sg-text-primary'
                            : 'border-sg-border-subtle bg-white text-sg-text-secondary hover:border-sg-border-focus hover:text-sg-text-primary'
                        }`}
                      >
                        <OptIcon className="h-5 w-5" />
                        <span className="text-xs font-medium">{opt.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Submit */}
              <button
                onClick={handleSubmit}
                disabled={!file || extractMutation.isPending}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-button bg-sg-primary py-3 text-sm font-semibold text-white transition-all hover:bg-sg-primary-hover disabled:opacity-50"
              >
                {extractMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Extract Data'
                )}
              </button>

              {extractMutation.isError && (
                <div className="mt-3 rounded-lg border border-vs-risk-red/20 bg-sg-risk-red-bg px-4 py-3 text-sm text-sg-risk-red">
                  {getErrorMessage(extractMutation.error)}
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="rounded-card border border-sg-border-subtle bg-white p-6 shadow-card lg:col-span-3">
              <h3 className="font-display text-base font-bold uppercase tracking-wider text-sg-text-primary">How It Works</h3>
              <div className="mt-4 space-y-4">
                {[
                  { step: '1', title: 'Upload Document', desc: 'Upload a contract, security assessment, or audit report in PDF or text format.' },
                  { step: '2', title: 'AI Processing', desc: 'Our NLP engine extracts structured risk data including contract terms, security controls, and compliance indicators.' },
                  { step: '3', title: 'Conflict Detection', desc: 'The system cross-references extracted data with existing vendor records to identify discrepancies.' },
                  { step: '4', title: 'Risk Flags', desc: 'Missing security controls, unusual terms, and other risk indicators are automatically flagged.' },
                ].map((item) => (
                  <div key={item.step} className="flex gap-4">
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-sg-surface-dim text-xs font-bold text-sg-text-primary">
                      {item.step}
                    </div>
                    <div>
                      <p className="font-display text-sm font-bold text-sg-text-primary">{item.title}</p>
                      <p className="text-sm text-sg-text-secondary">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Processing State */}
        {isProcessing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-8 flex flex-col items-center py-16"
          >
            <div className="relative">
              <div className="h-16 w-16 animate-spin-slow rounded-full border-2 border-black/10 border-t-sg-primary" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-bold text-sg-primary">{jobStatus?.progress_percent || 0}%</span>
              </div>
            </div>
            <p className="mt-6 text-lg font-bold text-sg-text-primary">Processing document...</p>
            <p className="mt-1 text-sm text-sg-text-secondary">{jobStatus?.stage || 'Initializing'}</p>
            <button
              onClick={handleReset}
              className="mt-4 text-sm font-semibold text-sg-text-secondary hover:text-sg-text-primary"
            >
              Cancel
            </button>
          </motion.div>
        )}

        {/* Completed State */}
        {isCompleted && jobStatus?.result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 space-y-6"
          >
            {/* Success header */}
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-8 w-8 text-sg-risk-green" />
              <div>
                <h2 className="font-display text-xl font-bold uppercase text-sg-text-primary">Extraction Complete</h2>
                <p className="text-sm text-sg-text-secondary">
                  Confidence score: {(jobStatus.result.confidence_score * 100).toFixed(0)}%
                </p>
              </div>
              <button
                onClick={handleReset}
                className="ml-auto rounded-button border border-sg-border-subtle bg-white px-4 py-2 text-sm font-semibold text-sg-text-secondary hover:text-sg-text-primary hover:border-sg-border-focus"
              >
                Process Another
              </button>
            </div>

            {/* Conflict Banner */}
            {hasConflicts && (
              <div className="rounded-card conflict-banner p-5">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-6 w-6 flex-shrink-0 text-sg-risk-red" />
                  <div>
                    <h3 className="text-lg font-semibold text-sg-risk-red">AI Detected Conflicts</h3>
                    <p className="mt-1 text-sm text-sg-text-secondary">
                      The extracted data contains inconsistencies that require review.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Conflict Cards */}
            {hasConflicts && (
              <div className="space-y-3">
                <h3 className="font-display text-base font-bold uppercase text-sg-text-primary">Conflicts ({jobStatus.result!.conflicts.length})</h3>
                {jobStatus.result!.conflicts.map((conflict, i) => (
                  <ConflictCard key={i} conflict={conflict} />
                ))}
              </div>
            )}

            {/* Risk Flags */}
            {jobStatus.result.risk_flags.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-display text-base font-bold uppercase text-sg-text-primary">Risk Flags ({jobStatus.result.risk_flags.length})</h3>
                <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  {jobStatus.result.risk_flags.map((flag, i) => (
                    <div key={i} className="rounded-card border border-vs-risk-yellow/15 bg-sg-surface p-4">
                      <div className="flex items-center gap-2">
                        <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          flag.severity === 'high' ? 'bg-sg-risk-red-bg text-sg-risk-red'
                          : flag.severity === 'medium' ? 'bg-sg-risk-yellow-bg text-sg-risk-yellow'
                          : 'bg-vs-text-tertiary/10 text-sg-text-secondary'
                        }`}>
                          {flag.severity}
                        </span>
                        <span className="font-mono text-xs text-sg-text-secondary">{flag.type}</span>
                      </div>
                      <p className="mt-2 text-sm text-sg-text-secondary">{flag.description}</p>
                      {flag.clause_reference && (
                        <p className="mt-1 font-mono text-[10px] text-sg-text-secondary">{flag.clause_reference}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted Data */}
            <div className="rounded-card border border-sg-border-subtle bg-white p-6 shadow-card">
              <h3 className="font-display text-base font-bold uppercase text-sg-text-primary">Extracted Data</h3>
              <div className="mt-4 overflow-x-auto rounded border border-sg-border-subtle bg-sg-surface-muted p-4">
                <pre className="text-xs leading-relaxed" style={{ fontFamily: 'JetBrains Mono' }}>
                  {JSON.stringify(jobStatus.result.extracted_data, null, 2)}
                </pre>
              </div>
            </div>
          </motion.div>
        )}

        {/* Failed State */}
        {isFailed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-8 flex flex-col items-center py-16"
          >
            <XCircle className="h-16 w-16 text-sg-risk-red" />
            <p className="mt-4 text-lg font-medium text-sg-risk-red">Extraction Failed</p>
            <p className="mt-1 text-sm text-sg-text-secondary">{jobStatus?.error?.message}</p>
            <button
              onClick={handleReset}
              className="mt-4 rounded-button bg-sg-primary px-6 py-2.5 text-sm font-semibold text-white hover:bg-sg-primary-hover"
            >
              Try Again
            </button>
          </motion.div>
        )}
      </div>
    </div>
  );
}
