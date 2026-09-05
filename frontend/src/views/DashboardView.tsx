import React, { useEffect, useState } from 'react';
import {
  Scale,
  CheckCircle2,
  AlertTriangle,
  Clock,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Loader2,
  UploadCloud,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import {
  ExceptionItem,
  ExceptionReport,
  ReconciliationReport,
} from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { SeverityBadge } from '../components/SeverityBadge';
import { ReconciliationOutcomeChart } from '../components/visualizations/ReconciliationOutcomeChart';
import { ExceptionBreakdownChart } from '../components/visualizations/ExceptionBreakdownChart';
import { formatCurrency, formatNumber, formatPercent } from '../utils/formatters';

interface DashboardViewProps {
  activeBatchId?: string | null;
  onNavigateToExceptions: (statusFilter?: string) => void;
  onNavigateToReconciliation: (statusFilter?: string) => void;
  onSelectTransaction: (transactionId: string) => void;
  onNavigateToUpload?: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  activeBatchId,
  onNavigateToExceptions,
  onNavigateToReconciliation,
  onSelectTransaction,
  onNavigateToUpload,
}) => {
  const [reconReport, setReconReport] = useState<ReconciliationReport | null>(null);
  const [exceptionReport, setExceptionReport] = useState<ExceptionReport | null>(null);
  const [pendingExceptions, setPendingExceptions] = useState<ExceptionItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [recon, exc, pending] = await Promise.all([
        api.getReconciliationReport(activeBatchId || undefined),
        api.getExceptionReport(activeBatchId || undefined),
        api.getExceptions({ review_status: 'PENDING', batch_id: activeBatchId || undefined }),
      ]);
      setReconReport(recon);
      setExceptionReport(exc);
      setPendingExceptions(pending);
      setIsLoading(false);
    } catch (err: any) {
      setIsLoading(false);
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to fetch dashboard metrics.');
      } else {
        setError(err.message || 'Unable to connect to the Finance Controller API.');
      }
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [activeBatchId]);

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center gap-3 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className="text-xs font-mono">Loading real-time financial controller metrics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto my-8 p-6 bg-slate-900 border border-rose-800 rounded-xl text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
        <h3 className="text-base font-semibold text-white">Dashboard Telemetry Error</h3>
        <p className="text-xs text-rose-300 font-mono">{error}</p>
        <button
          onClick={loadDashboardData}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-semibold transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Connection
        </button>
      </div>
    );
  }

  const totalRecords = reconReport?.total_records ?? 0;
  const matchedRecords = reconReport?.matched ?? 0;
  const matchRate = reconReport?.match_rate ?? 0;
  const exceptionCount = reconReport?.unresolved ?? 0;
  const resolvedCount = exceptionReport?.resolved_count ?? 0;
  const totalVariance = exceptionReport?.total_financial_difference ?? 0;
  const pendingCount = pendingExceptions.length;

  if (totalRecords === 0) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-slate-900 border border-slate-800 rounded-2xl text-center space-y-6 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-blue-950/60 border border-blue-800/80 flex items-center justify-center text-blue-400 mx-auto shadow-lg shadow-blue-950/50">
          <UploadCloud className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-white tracking-tight">Finance Operations Control Center</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            The workspace starts completely empty. Ingest custom financial records by uploading Payment Gateway, Bank Statement, and General Ledger CSV exports to initiate automated 3-way reconciliation and AI exception root-cause analysis.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          {onNavigateToUpload && (
            <button
              onClick={onNavigateToUpload}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-blue-900/30 transition"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload & Ingest Financial Batch</span>
            </button>
          )}
        </div>
        <div className="text-[11px] text-slate-500 font-mono border-t border-slate-800/80 pt-4">
          Strict Evidence First • Production LLM Integration • Isolated by Analysis ID
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Executive Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Executive Reconciliation Dashboard</h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated 3-way multi-source verification and human-in-the-loop exception governance
          </p>
        </div>
        <button
          onClick={loadDashboardData}
          className="self-start sm:self-auto inline-flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-md text-xs font-medium transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Ingested */}
        <div
          onClick={() => onNavigateToReconciliation('ALL')}
          className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between cursor-pointer hover:border-blue-500/50 hover:shadow-lg transition group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Ingested Transactions
            </span>
            <Scale className="w-4 h-4 text-blue-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold font-mono text-white tabular-nums">{formatNumber(totalRecords)}</div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Reconciled 3-way records
            </p>
          </div>
        </div>

        {/* Match Rate */}
        <div
          onClick={() => onNavigateToReconciliation('MATCHED')}
          className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between cursor-pointer hover:border-emerald-500/50 hover:shadow-lg transition group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Clean Match Rate
            </span>
            <TrendingUp className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold font-mono text-emerald-400 tabular-nums">
              {formatPercent(matchRate)}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              <span className="text-emerald-400 font-mono font-semibold">{formatNumber(matchedRecords)}</span> of {formatNumber(totalRecords)} matched exactly
            </p>
          </div>
        </div>

        {/* Exceptions & Variance */}
        <div
          onClick={() => onNavigateToExceptions('ALL')}
          className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between cursor-pointer hover:border-rose-500/50 hover:shadow-lg transition group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Identified Exceptions
            </span>
            <AlertTriangle className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold font-mono text-rose-400 tabular-nums">{formatNumber(exceptionCount)}</div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Net Discrepancy: <span className="font-mono font-semibold text-rose-400">{formatCurrency(totalVariance)}</span>
            </p>
          </div>
        </div>

        {/* Governance Queue */}
        <div
          onClick={() => onNavigateToExceptions('PENDING')}
          className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between cursor-pointer hover:border-amber-500/50 hover:shadow-lg transition group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Pending Human Review
            </span>
            <Clock className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold font-mono text-amber-400 tabular-nums">{formatNumber(pendingCount)}</div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Resolved / Closed: <span className="font-mono text-emerald-400 font-semibold">{formatNumber(resolvedCount)}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Visual Analytics Telemetry: Reconciliation Outcome & Exception Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ReconciliationOutcomeChart
          totalRecords={totalRecords}
          matchedCount={matchedRecords}
          exceptionCount={exceptionCount}
          matchRate={matchRate}
        />
        <ExceptionBreakdownChart
          exceptionBreakdown={reconReport?.exception_breakdown || {}}
          totalExceptions={exceptionCount}
        />
      </div>

      {/* Critical Triage Queue */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
              Exceptions Awaiting Human Review ({pendingExceptions.length})
            </h3>
          </div>
          <button
            onClick={() => onNavigateToExceptions('PENDING')}
            className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 transition"
          >
            <span>Open Exception Workbench</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {pendingExceptions.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            All exceptions have been reviewed and resolved!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-mono text-[11px]">
                <tr>
                  <th className="px-4 py-3">Exception ID</th>
                  <th className="px-4 py-3">Transaction ID</th>
                  <th className="px-4 py-3">Classification</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Discrepancy</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-sans">
                {pendingExceptions.slice(0, 5).map((exc) => (
                  <tr key={exc.exception_id} className="hover:bg-slate-850/50 transition">
                    <td className="px-4 py-3 font-mono font-semibold text-blue-400">
                      {exc.exception_id}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-200">
                      <button
                        onClick={() => onSelectTransaction(exc.transaction_id)}
                        className="hover:underline hover:text-blue-300"
                        title="Click to view 3-way reconciliation drawer"
                      >
                        {exc.transaction_id}
                      </button>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">{exc.exception_type}</td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={exc.severity} />
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-rose-400 tabular-nums">
                      {exc.difference !== null ? formatCurrency(exc.difference) : 'N/A'}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={exc.review_status} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => onNavigateToExceptions()}
                        className="px-2.5 py-1 rounded bg-blue-600/20 text-blue-300 border border-blue-500/40 hover:bg-blue-600 hover:text-white transition text-xs"
                      >
                        Review & AI Investigate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
