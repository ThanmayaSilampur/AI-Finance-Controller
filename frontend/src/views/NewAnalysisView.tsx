import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Loader2,
  Check,
} from 'lucide-react';
import { api } from '../api/client';
import { AnalysisBatch } from '../api/types';

interface NewAnalysisViewProps {
  onAnalysisComplete: (batch: AnalysisBatch) => void;
  onCancel?: () => void;
}

export const NewAnalysisView: React.FC<NewAnalysisViewProps> = ({
  onAnalysisComplete,
  onCancel,
}) => {
  const [paymentFile, setPaymentFile] = useState<File | null>(null);
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [ledgerFile, setLedgerFile] = useState<File | null>(null);
  const [batchName, setBatchName] = useState<string>('');

  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingStep, setProcessingStep] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const paymentInputRef = useRef<HTMLInputElement>(null);
  const bankInputRef = useRef<HTMLInputElement>(null);
  const ledgerInputRef = useRef<HTMLInputElement>(null);

  const steps = [
    'Parsing & Normalizing CSV Schemas',
    'Executing 3-Way Deterministic Reconciliation',
    'Categorizing Financial Exceptions & Discrepancies',
    'Persisting Immutable Audit Trail & Lineage',
  ];

  const handleStartAnalysis = async () => {
    if (!paymentFile || !bankFile || !ledgerFile) {
      setError('Please provide all three data sources (Payment, Bank, Ledger) to run 3-way reconciliation.');
      return;
    }

    try {
      setIsProcessing(true);
      setError(null);
      setProcessingStep(0);

      const stepTimer = setInterval(() => {
        setProcessingStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
      }, 500);

      const result = await api.uploadAnalysis(
        paymentFile,
        bankFile,
        ledgerFile,
        batchName.trim() || undefined
      );

      clearInterval(stepTimer);
      setProcessingStep(steps.length);
      setTimeout(() => {
        onAnalysisComplete(result);
      }, 600);
    } catch (err: any) {
      setIsProcessing(false);
      setError(err.message || 'Analysis processing failed.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <UploadCloud className="w-6 h-6 text-blue-500" />
            <span>Ingest & Reconcile Financial Batch</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Upload custom CSV files from your payment gateway, bank statements, and general ledger.
          </p>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-rose-950/40 border border-rose-800/80 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-200">
            <p className="font-semibold text-rose-100">Ingestion Error</p>
            <p className="mt-1 font-mono text-[11px] break-all">{error}</p>
          </div>
        </div>
      )}

      {/* Batch Name Input */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
          Batch Identifier / Description (Optional)
        </label>
        <input
          type="text"
          value={batchName}
          onChange={(e) => setBatchName(e.target.value)}
          disabled={isProcessing}
          placeholder="e.g., September 2026 Monthly Settlement Run"
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition font-mono"
        />
      </div>

      {/* 3-Source Upload Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Source 1: Payment Gateway */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                1. Payment Gateway
              </span>
              <FileSpreadsheet className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Gateway settlement export (e.g. Razorpay, Stripe)
            </p>
          </div>

          <input
            type="file"
            ref={paymentInputRef}
            accept=".csv"
            onChange={(e) => setPaymentFile(e.target.files?.[0] || null)}
            className="hidden"
          />

          <div
            onClick={() => !isProcessing && paymentInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[110px] ${
              paymentFile
                ? 'border-blue-500/60 bg-blue-950/20'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/50'
            }`}
          >
            {paymentFile ? (
              <>
                <CheckCircle2 className="w-6 h-6 text-blue-400 mb-1" />
                <span className="text-xs font-medium text-white break-all">{paymentFile.name}</span>
                <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                  {(paymentFile.size / 1024).toFixed(1)} KB
                </span>
              </>
            ) : (
              <>
                <UploadCloud className="w-6 h-6 text-slate-500 mb-1" />
                <span className="text-xs font-medium text-slate-300">Select payment.csv</span>
                <span className="text-[10px] text-slate-600 mt-0.5">Click to browse</span>
              </>
            )}
          </div>
        </div>

        {/* Source 2: Bank Statement */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                2. Bank Statement
              </span>
              <FileSpreadsheet className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Bank transaction feed or statement export
            </p>
          </div>

          <input
            type="file"
            ref={bankInputRef}
            accept=".csv"
            onChange={(e) => setBankFile(e.target.files?.[0] || null)}
            className="hidden"
          />

          <div
            onClick={() => !isProcessing && bankInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[110px] ${
              bankFile
                ? 'border-emerald-500/60 bg-emerald-950/20'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/50'
            }`}
          >
            {bankFile ? (
              <>
                <CheckCircle2 className="w-6 h-6 text-emerald-400 mb-1" />
                <span className="text-xs font-medium text-white break-all">{bankFile.name}</span>
                <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                  {(bankFile.size / 1024).toFixed(1)} KB
                </span>
              </>
            ) : (
              <>
                <UploadCloud className="w-6 h-6 text-slate-500 mb-1" />
                <span className="text-xs font-medium text-slate-300">Select bank.csv</span>
                <span className="text-[10px] text-slate-600 mt-0.5">Click to browse</span>
              </>
            )}
          </div>
        </div>

        {/* Source 3: General Ledger */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
                3. General Ledger
              </span>
              <FileSpreadsheet className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Internal accounting ledger entries (ERP)
            </p>
          </div>

          <input
            type="file"
            ref={ledgerInputRef}
            accept=".csv"
            onChange={(e) => setLedgerFile(e.target.files?.[0] || null)}
            className="hidden"
          />

          <div
            onClick={() => !isProcessing && ledgerInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[110px] ${
              ledgerFile
                ? 'border-purple-500/60 bg-purple-950/20'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/50'
            }`}
          >
            {ledgerFile ? (
              <>
                <CheckCircle2 className="w-6 h-6 text-purple-400 mb-1" />
                <span className="text-xs font-medium text-white break-all">{ledgerFile.name}</span>
                <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                  {(ledgerFile.size / 1024).toFixed(1)} KB
                </span>
              </>
            ) : (
              <>
                <UploadCloud className="w-6 h-6 text-slate-500 mb-1" />
                <span className="text-xs font-medium text-slate-300">Select ledger.csv</span>
                <span className="text-[10px] text-slate-600 mt-0.5">Click to browse</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Processing Animation / Progress */}
      {isProcessing && (
        <div className="bg-slate-900 border border-blue-900/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
            <span className="text-sm font-semibold text-white">Running Automated Ingestion & Matching...</span>
          </div>

          <div className="space-y-2">
            {steps.map((step, idx) => {
              const isDone = processingStep > idx;
              const isCurrent = processingStep === idx;
              return (
                <div key={step} className="flex items-center gap-2.5 text-xs">
                  {isDone ? (
                    <Check className="w-4 h-4 text-emerald-400" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-700" />
                  )}
                  <span className={isDone ? 'text-slate-300' : isCurrent ? 'text-blue-200 font-medium' : 'text-slate-600'}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2">
        {onCancel ? (
          <button
            onClick={onCancel}
            disabled={isProcessing}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white transition disabled:opacity-50"
          >
            Cancel
          </button>
        ) : (
          <div />
        )}

        <button
          onClick={handleStartAnalysis}
          disabled={!paymentFile || !bankFile || !ledgerFile || isProcessing}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-900/30 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <span>Run Reconciliation Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
