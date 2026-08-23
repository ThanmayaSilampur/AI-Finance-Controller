import React, { useEffect, useState } from 'react';
import {
  X,
  CreditCard,
  Building2,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  Scale,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import { SourceRecord, TransactionDetail } from '../api/types';
import { StatusBadge } from './StatusBadge';

interface TransactionDetailDrawerProps {
  transactionId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const TransactionDetailDrawer: React.FC<TransactionDetailDrawerProps> = ({
  transactionId,
  isOpen,
  onClose,
}) => {
  const [detail, setDetail] = useState<TransactionDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && transactionId) {
      setIsLoading(true);
      setError(null);
      api
        .getTransaction(transactionId)
        .then((res) => {
          setDetail(res);
          setIsLoading(false);
        })
        .catch((err) => {
          setError(err.message || 'Failed to load transaction details.');
          setIsLoading(false);
        });
    } else {
      setDetail(null);
    }
  }, [isOpen, transactionId]);

  if (!isOpen) return null;

  const renderSourceCard = (
    title: string,
    icon: React.ReactNode,
    record?: SourceRecord,
    normalizedVal?: string | null
  ) => {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-xs uppercase tracking-wider">
              {icon}
              {title}
            </div>
            {record ? (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {record.status || 'UNKNOWN'}
              </span>
            ) : (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                MISSING
              </span>
            )}
          </div>

          {record ? (
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-slate-500 text-[11px] block">Raw Amount</span>
                <span className="font-mono text-sm font-semibold text-white">
                  {record.currency} {parseFloat(record.amount || '0').toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[11px] block">Normalized Value</span>
                <span className="font-mono text-xs text-blue-400 font-semibold">
                  {normalizedVal ? `₹${parseFloat(normalizedVal).toFixed(2)}` : 'N/A'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <span className="text-slate-500 text-[10px] block">Date</span>
                  <span className="font-mono text-slate-300 text-[11px]">
                    {record.transaction_date || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block">Ref ID</span>
                  <span className="font-mono text-slate-300 text-[11px] truncate block" title={record.reference_id || ''}>
                    {record.reference_id || 'N/A'}
                  </span>
                </div>
              </div>
              {record.customer_id && (
                <div>
                  <span className="text-slate-500 text-[10px] block">Customer ID</span>
                  <span className="font-mono text-slate-300 text-[11px]">{record.customer_id}</span>
                </div>
              )}
              {record.order_id && (
                <div>
                  <span className="text-slate-500 text-[10px] block">Order ID</span>
                  <span className="font-mono text-slate-300 text-[11px]">{record.order_id}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="py-6 text-center text-slate-500 text-xs italic">
              No matching record received in this source.
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col h-full overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-blue-600/20 text-blue-400 border border-blue-500/30">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-white">3-Way Transaction Reconciliation</h2>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-blue-300 border border-slate-700">
                  {transactionId}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic comparison across Payment System, Bank Statement, and Ledger
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 flex-1">
          {isLoading && (
            <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
              <span className="text-xs font-mono">Loading transaction records from backend...</span>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {detail && (
            <>
              {/* Reconciliation Status Overview */}
              {detail.reconciliation_result && (
                <div
                  className={`p-4 rounded-lg border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
                    detail.reconciliation_result.matched
                      ? 'bg-emerald-950/40 border-emerald-800/80'
                      : 'bg-rose-950/40 border-rose-800/80'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {detail.reconciliation_result.matched ? (
                      <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-6 h-6 text-rose-400" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider text-white">
                          Reconciliation Result:
                        </span>
                        <StatusBadge
                          status={detail.reconciliation_result.matched ? 'MATCHED' : 'EXCEPTION'}
                          size="sm"
                        />
                      </div>
                      <p className="text-xs text-slate-300 mt-1">
                        {detail.reconciliation_result.explanations?.join(' ') ||
                          (detail.reconciliation_result.matched
                            ? 'All records matched across all verified source criteria.'
                            : `Exception identified: ${detail.reconciliation_result.exception_type}`)}
                      </p>
                    </div>
                  </div>

                  <div className="text-right font-mono text-xs flex-shrink-0">
                    <span className="text-slate-400 block text-[11px]">Match Score</span>
                    <span className="text-sm font-bold text-white">
                      {(detail.reconciliation_result.match_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}

              {/* 3-Way Source Comparison Grid */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
                  <span>Source System Verification</span>
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {renderSourceCard(
                    'Payment Source',
                    <CreditCard className="w-4 h-4 text-blue-400" />,
                    detail.source_records?.payment,
                    detail.normalized_values?.payment
                  )}
                  {renderSourceCard(
                    'Bank Statement',
                    <Building2 className="w-4 h-4 text-emerald-400" />,
                    detail.source_records?.bank,
                    detail.normalized_values?.bank
                  )}
                  {renderSourceCard(
                    'Internal Ledger',
                    <BookOpen className="w-4 h-4 text-purple-400" />,
                    detail.source_records?.ledger,
                    detail.normalized_values?.ledger
                  )}
                </div>
              </div>

              {/* Match Details & Rule Evaluation */}
              {detail.reconciliation_result && (
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Matching Rule Audit & Recommended Action
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-slate-500 block text-[11px]">Recommended Action</span>
                      <span className="font-mono text-emerald-300 font-semibold flex items-center gap-1.5 mt-0.5">
                        <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
                        {detail.reconciliation_result.recommended_action}
                      </span>
                    </div>
                    {detail.reconciliation_result.exception_type && (
                      <div>
                        <span className="text-slate-500 block text-[11px]">Exception Classification</span>
                        <span className="font-mono text-rose-300 font-semibold mt-0.5 block">
                          {detail.reconciliation_result.exception_type}
                        </span>
                      </div>
                    )}
                  </div>

                  {detail.reconciliation_result.details && (
                    <div className="pt-2 border-t border-slate-800">
                      <span className="text-[11px] text-slate-500 block mb-1">Rule Details:</span>
                      <pre className="text-[11px] font-mono bg-slate-950 p-2.5 rounded border border-slate-850 text-slate-300 overflow-x-auto">
                        {JSON.stringify(detail.reconciliation_result.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-900 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-white rounded text-xs font-medium transition"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
};
