import React, { useEffect, useState } from 'react';
import {
  History,
  FileCode,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import { AuditHistory, TransactionSummary } from '../api/types';
import { AuditTimeline } from '../components/AuditTimeline';

interface AuditViewProps {
  initialTransactionId?: string | null;
}

export const AuditView: React.FC<AuditViewProps> = ({ initialTransactionId }) => {
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [selectedTxnId, setSelectedTxnId] = useState<string>(initialTransactionId || '');
  const [auditData, setAuditData] = useState<AuditHistory | null>(null);
  const [isLoadingAudit, setIsLoadingAudit] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState<boolean>(false);

  // Load available transactions list for quick dropdown selection
  useEffect(() => {
    api
      .getTransactions()
      .then((res) => {
        setTransactions(res);
        if (!selectedTxnId && res.length > 0) {
          const firstException = res.find((t) => t.status === 'EXCEPTION');
          const defaultId = firstException ? firstException.transaction_id : res[0].transaction_id;
          setSelectedTxnId(defaultId);
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to load transaction index.');
      });
  }, []);

  const loadAuditHistory = async (txnId: string) => {
    if (!txnId) return;
    try {
      setIsLoadingAudit(true);
      setError(null);
      const data = await api.getAuditHistory(txnId);
      setAuditData(data);
      setIsLoadingAudit(false);
    } catch (err: any) {
      setIsLoadingAudit(false);
      if (err instanceof ApiError) {
        setError(err.message || `Audit record not found for transaction ${txnId}`);
      } else {
        setError(err.message || 'Failed to fetch audit trail.');
      }
    }
  };

  useEffect(() => {
    if (selectedTxnId) {
      loadAuditHistory(selectedTxnId);
    }
  }, [selectedTxnId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Audit & Governance Trail</h1>
          <p className="text-xs text-slate-400 mt-1">
            Complete immutable transaction lifecycle, AI investigations, state transitions, and reviewer sign-offs
          </p>
        </div>
        <button
          onClick={() => loadAuditHistory(selectedTxnId)}
          disabled={!selectedTxnId || isLoadingAudit}
          className="self-start sm:self-auto inline-flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-md text-xs font-medium transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isLoadingAudit ? 'animate-spin' : ''}`} />
          <span>Refresh Trail</span>
        </button>
      </div>

      {/* Transaction Selector Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="w-full sm:w-auto flex-1 flex items-center gap-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 whitespace-nowrap">
            Select Transaction:
          </label>
          <div className="relative flex-1 max-w-xs">
            <select
              value={selectedTxnId}
              onChange={(e) => setSelectedTxnId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
            >
              {transactions.map((tx) => (
                <option key={tx.transaction_id} value={tx.transaction_id}>
                  {tx.transaction_id} ({tx.status} {tx.exception_type ? `• ${tx.exception_type}` : ''})
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={() => setShowRawJson(!showRawJson)}
          className="px-3 py-1.5 rounded bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono transition flex items-center gap-1.5 self-end sm:self-auto"
        >
          <FileCode className="w-3.5 h-3.5 text-blue-400" />
          <span>{showRawJson ? 'Hide Raw Audit JSON' : 'Inspect Raw Audit JSON'}</span>
        </button>
      </div>

      {/* Content */}
      {isLoadingAudit ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="text-xs font-mono">Fetching chronological audit trail from store...</span>
        </div>
      ) : error ? (
        <div className="p-6 bg-slate-900 border border-rose-800 rounded-xl text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
          <p className="text-xs text-rose-300 font-mono">{error}</p>
        </div>
      ) : auditData ? (
        <div className="space-y-6">
          {/* Quick Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <span className="text-slate-500 block text-[11px]">Audit Store Records</span>
              <span className="text-lg font-bold text-white mt-1 block">
                {auditData.audit_records?.length || 0}
              </span>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <span className="text-slate-500 block text-[11px]">Advisory AI Investigations</span>
              <span className="text-lg font-bold text-purple-400 mt-1 block">
                {auditData.investigations?.length || 0}
              </span>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <span className="text-slate-500 block text-[11px]">Human Review Actions</span>
              <span className="text-lg font-bold text-emerald-400 mt-1 block">
                {auditData.review_actions?.length || 0}
              </span>
            </div>
          </div>

          {/* Timeline View */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-4 shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-white flex items-center gap-2">
                <History className="w-4 h-4 text-blue-400" />
                <span>Lifecycle & Governance Timeline</span>
              </h3>
              <span className="font-mono text-xs text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-850">
                Transaction: {selectedTxnId}
              </span>
            </div>

            <AuditTimeline
              auditRecords={auditData.audit_records}
              reviewActions={auditData.review_actions}
              investigations={auditData.investigations}
            />
          </div>

          {/* Raw JSON Inspector */}
          {showRawJson && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-mono text-slate-400">Raw Audit Payload:</span>
                <span className="text-[11px] font-mono text-slate-500">GET /audit/{selectedTxnId}</span>
              </div>
              <pre className="text-[11px] font-mono bg-slate-950 p-4 rounded-md border border-slate-850 text-emerald-300 overflow-x-auto max-h-96">
                {JSON.stringify(auditData, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
