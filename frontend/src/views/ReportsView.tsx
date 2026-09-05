import React, { useEffect, useState } from 'react';
import {
  FileSpreadsheet,
  FileCode,
  TrendingUp,
  AlertTriangle,
  Scale,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import { ExceptionReport, ReconciliationReport } from '../api/types';
import { ReconciliationOutcomeChart } from '../components/visualizations/ReconciliationOutcomeChart';
import { ExceptionBreakdownChart } from '../components/visualizations/ExceptionBreakdownChart';
import { formatCurrency, formatNumber, formatPercent } from '../utils/formatters';

interface ReportsViewProps {
  activeBatchId?: string | null;
}

export const ReportsView: React.FC<ReportsViewProps> = ({ activeBatchId }) => {
  const [reconReport, setReconReport] = useState<ReconciliationReport | null>(null);
  const [exceptionReport, setExceptionReport] = useState<ExceptionReport | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isExportingJson, setIsExportingJson] = useState<boolean>(false);
  const [isExportingCsv, setIsExportingCsv] = useState<boolean>(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  const loadReports = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [recon, exc] = await Promise.all([
        api.getReconciliationReport(activeBatchId || undefined),
        api.getExceptionReport(activeBatchId || undefined),
      ]);
      setReconReport(recon);
      setExceptionReport(exc);
      setIsLoading(false);
    } catch (err: any) {
      setIsLoading(false);
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to generate financial reports.');
      } else {
        setError(err.message || 'Unable to connect to the Finance Controller API.');
      }
    }
  };

  useEffect(() => {
    loadReports();
  }, [activeBatchId]);

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      if (format === 'json') setIsExportingJson(true);
      if (format === 'csv') setIsExportingCsv(true);
      setExportMessage(null);

      await api.exportExceptions(format, activeBatchId || undefined);

      setExportMessage(`Successfully exported exception report as ${format.toUpperCase()}.`);
      if (format === 'json') setIsExportingJson(false);
      if (format === 'csv') setIsExportingCsv(false);

      setTimeout(() => setExportMessage(null), 4000);
    } catch (err: any) {
      if (format === 'json') setIsExportingJson(false);
      if (format === 'csv') setIsExportingCsv(false);
      alert(err.message || `Export failed for format ${format}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Financial Reports & Exports</h1>
        </div>

        {/* Export Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('json')}
            disabled={isExportingJson || isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 rounded-md text-xs font-mono transition disabled:opacity-50"
          >
            {isExportingJson ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileCode className="w-3.5 h-3.5 text-blue-400" />
            )}
            <span>Export JSON</span>
          </button>

          <button
            onClick={() => handleExport('csv')}
            disabled={isExportingCsv || isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-950 border border-emerald-800 hover:border-emerald-700 text-emerald-300 rounded-md text-xs font-mono transition disabled:opacity-50"
          >
            {isExportingCsv ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {exportMessage && (
        <div className="p-3 rounded-lg bg-emerald-950/80 border border-emerald-700 text-emerald-300 text-xs flex items-center gap-2 font-mono">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{exportMessage}</span>
        </div>
      )}

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="text-xs font-mono">Aggregating multi-source financial metrics...</span>
        </div>
      ) : error ? (
        <div className="p-6 bg-slate-900 border border-rose-800 rounded-xl text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
          <p className="text-xs text-rose-300 font-mono">{error}</p>
          <button
            onClick={loadReports}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Visual Analysis Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ReconciliationOutcomeChart
              totalRecords={reconReport?.total_records ?? 0}
              matchedCount={reconReport?.matched ?? 0}
              exceptionCount={reconReport?.unresolved ?? 0}
              matchRate={reconReport?.match_rate}
              title="Reconciliation Outcome"
            />
            <ExceptionBreakdownChart
              exceptionBreakdown={exceptionReport?.exception_breakdown || reconReport?.exception_breakdown || {}}
              totalExceptions={exceptionReport?.exception_count ?? reconReport?.unresolved ?? 0}
              title="Exception Breakdown"
            />
          </div>

          {/* Top Report Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Reconciliation Performance */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Scale className="w-4 h-4 text-blue-400" />
                <span>Reconciliation Performance</span>
              </h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Total Records:</span>
                  <span className="font-bold text-white tabular-nums">{formatNumber(reconReport?.total_records ?? 0)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Matched Cleanly:</span>
                  <span className="font-bold text-emerald-400 tabular-nums">{formatNumber(reconReport?.matched ?? 0)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Unresolved Exceptions:</span>
                  <span className="font-bold text-rose-400 tabular-nums">{formatNumber(reconReport?.unresolved ?? 0)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Match Rate:</span>
                  <span className="font-bold text-emerald-400 tabular-nums">{formatPercent(reconReport?.match_rate ?? 0)}</span>
                </div>
              </div>
            </div>

            {/* Exception Financial Summary */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <span>Exception Variance</span>
              </h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Total Exceptions:</span>
                  <span className="font-bold text-rose-400 tabular-nums">{formatNumber(exceptionReport?.exception_count ?? 0)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Total Discrepancy Amount:</span>
                  <span className="font-bold text-rose-400 tabular-nums">
                    {formatCurrency(exceptionReport?.total_financial_difference ?? 0)}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Resolved Exceptions:</span>
                  <span className="font-bold text-emerald-400 tabular-nums">{formatNumber(exceptionReport?.resolved_count ?? 0)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Resolution Rate:</span>
                  <span className="font-bold text-emerald-400 tabular-nums">
                    {formatPercent(exceptionReport?.resolution_rate ?? 0)}
                  </span>
                </div>
              </div>
            </div>

            {/* Governance & Audit State */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-purple-400" />
                <span>Controller Governance</span>
              </h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Batch Type:</span>
                  <span className="text-slate-200">Synthetic Multi-Source (3 Sources)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">Reconciliation Engine:</span>
                  <span className="text-slate-200">Deterministic Matching</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-855">
                  <span className="text-slate-400">AI Role:</span>
                  <span className="text-purple-300">Read-Only Advisory</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Audit Trail:</span>
                  <span className="text-emerald-400">JSON Immutable Store</span>
                </div>
              </div>
            </div>
          </div>

          {/* High-Value / Unresolved Exceptions Table */}
          {exceptionReport?.high_value_unresolved_exceptions &&
            exceptionReport.high_value_unresolved_exceptions.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
                    Unresolved Exceptions Summary ({exceptionReport.high_value_unresolved_exceptions.length})
                  </h3>
                  <span className="text-xs font-mono text-slate-500">
                    GET /reports/exceptions
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-mono text-[11px]">
                      <tr>
                        <th className="px-4 py-3">Transaction ID</th>
                        <th className="px-4 py-3">Exception Classification</th>
                        <th className="px-4 py-3">Recommended Next Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 font-sans">
                      {exceptionReport.high_value_unresolved_exceptions.map((item) => (
                        <tr key={item.transaction_id} className="hover:bg-slate-850/50 transition">
                          <td className="px-4 py-3 font-mono font-semibold text-blue-400">
                            {item.transaction_id}
                          </td>
                          <td className="px-4 py-3 font-mono text-rose-300">
                            {item.exception_type}
                          </td>
                          <td className="px-4 py-3 font-mono text-slate-300">
                            {item.recommended_action}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
        </div>
      )}
    </div>
  );
};
