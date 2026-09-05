import React, { useEffect, useState, useMemo } from 'react';
import {
  AlertTriangle,
  BrainCircuit,
  ShieldCheck,
  Search,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  History,
  Scale,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import {
  ExceptionItem,
  InvestigationResponse,
  ReviewResponse,
} from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { SeverityBadge } from '../components/SeverityBadge';
import { AIInvestigationCard } from '../components/AIInvestigationCard';
import { ReviewActionModal } from '../components/ReviewActionModal';
import { TransactionDetailDrawer } from '../components/TransactionDetailDrawer';
import { ThreeWayEvidenceVisualizer } from '../components/visualizations/ThreeWayEvidenceVisualizer';
import { InvestigationPipeline } from '../components/visualizations/InvestigationPipeline';
import { formatCurrency } from '../utils/formatters';

interface ExceptionsViewProps {
  activeBatchId?: string | null;
  initialStatusFilter?: string;
  onNavigateToAudit?: (transactionId: string) => void;
}

export const ExceptionsView: React.FC<ExceptionsViewProps> = ({
  activeBatchId,
  initialStatusFilter,
}) => {
  const [exceptions, setExceptions] = useState<ExceptionItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [reviewStatusFilter, setReviewStatusFilter] = useState<string>(initialStatusFilter || 'ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [exceptionTypeFilter, setExceptionTypeFilter] = useState<string>('ALL');

  // Interactive AI & Review state per exception
  const [investigations, setInvestigations] = useState<Record<string, InvestigationResponse>>({});
  const [investigatingIds, setInvestigatingIds] = useState<Record<string, boolean>>({});
  const [investigationErrors, setInvestigationErrors] = useState<Record<string, string>>({});
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [activeReviewException, setActiveReviewException] = useState<ExceptionItem | null>(null);
  const [drawerTxnId, setDrawerTxnId] = useState<string | null>(null);

  const loadExceptions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.getExceptions({
        batch_id: activeBatchId || undefined,
      });
      setExceptions(res);
      setIsLoading(false);
    } catch (err: any) {
      setIsLoading(false);
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to load exception queue.');
      } else {
        setError(err.message || 'Unable to connect to the Finance Controller API.');
      }
    }
  };

  useEffect(() => {
    loadExceptions();
  }, [activeBatchId]);

  const handleInvestigate = async (exceptionId: string) => {
    try {
      setInvestigatingIds((prev) => ({ ...prev, [exceptionId]: true }));
      setInvestigationErrors((prev) => {
        const copy = { ...prev };
        delete copy[exceptionId];
        return copy;
      });
      const inv = await api.investigateException(exceptionId);
      setInvestigations((prev) => ({ ...prev, [exceptionId]: inv }));
      setExpandedIds((prev) => ({ ...prev, [exceptionId]: true }));
      setInvestigatingIds((prev) => ({ ...prev, [exceptionId]: false }));
    } catch (err: any) {
      setInvestigatingIds((prev) => ({ ...prev, [exceptionId]: false }));
      setInvestigationErrors((prev) => ({
        ...prev,
        [exceptionId]: err.message || 'AI Investigation failed: LLM Provider is not configured or connection failed.',
      }));
      setExpandedIds((prev) => ({ ...prev, [exceptionId]: true }));
    }
  };

  const handleReviewSuccess = (updated: ReviewResponse) => {
    setExceptions((prev) =>
      prev.map((item) => {
        if (item.exception_id === updated.exception_id || item.audit_id === updated.audit_id) {
          return {
            ...item,
            review_status: updated.review_status,
            review_history: updated.review_history,
          };
        }
        return item;
      })
    );
  };

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Available unique types
  const availableTypes = useMemo(() => {
    const set = new Set<string>();
    exceptions.forEach((e) => {
      if (e.exception_type) set.add(e.exception_type);
    });
    return Array.from(set).sort();
  }, [exceptions]);

  // Filtered exceptions
  const filteredExceptions = useMemo(() => {
    return exceptions.filter((exc) => {
      const matchesSearch =
        !searchQuery.trim() ||
        exc.exception_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        exc.transaction_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        exc.exception_type.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus =
        reviewStatusFilter === 'ALL' ||
        exc.review_status.toUpperCase() === reviewStatusFilter.toUpperCase();

      const matchesSeverity =
        severityFilter === 'ALL' ||
        exc.severity.toUpperCase() === severityFilter.toUpperCase();

      const matchesType =
        exceptionTypeFilter === 'ALL' ||
        exc.exception_type === exceptionTypeFilter;

      return matchesSearch && matchesStatus && matchesSeverity && matchesType;
    });
  }, [exceptions, searchQuery, reviewStatusFilter, severityFilter, exceptionTypeFilter]);

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, reviewStatusFilter, severityFilter, exceptionTypeFilter, activeBatchId]);

  const totalPages = Math.max(1, Math.ceil(filteredExceptions.length / pageSize));
  const paginatedExceptions = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredExceptions.slice(start, start + pageSize);
  }, [filteredExceptions, currentPage, pageSize]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Exception Investigation Workbench</h1>
        </div>
        <button
          onClick={loadExceptions}
          className="self-start sm:self-auto inline-flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-md text-xs font-medium transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
          <span>Reload Queue</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 grid grid-cols-1 sm:grid-cols-4 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search Exception or TX ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <select
            value={reviewStatusFilter}
            onChange={(e) => setReviewStatusFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
          >
            <option value="ALL">All Review States</option>
            <option value="PENDING">PENDING Only</option>
            <option value="APPROVED">APPROVED Only</option>
            <option value="REJECTED">REJECTED Only</option>
            <option value="ESCALATED">ESCALATED Only</option>
          </select>
        </div>

        {/* Severity Filter */}
        <div>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
          >
            <option value="ALL">All Severity Levels</option>
            <option value="HIGH">HIGH Severity</option>
            <option value="MEDIUM">MEDIUM Severity</option>
            <option value="LOW">LOW Severity</option>
          </select>
        </div>

        {/* Exception Type */}
        <div>
          <select
            value={exceptionTypeFilter}
            onChange={(e) => setExceptionTypeFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
          >
            <option value="ALL">All Exception Types</option>
            {availableTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Exception Cards Stream */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="text-xs font-mono">Fetching exception records from audit store...</span>
        </div>
      ) : error ? (
        <div className="p-6 bg-slate-900 border border-rose-800 rounded-xl text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
          <p className="text-xs text-rose-300 font-mono">{error}</p>
          <button
            onClick={loadExceptions}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : filteredExceptions.length === 0 ? (
        <div className="py-16 text-center text-xs text-slate-400 bg-slate-900 rounded-lg border border-slate-800">
          No exceptions match the selected filter criteria.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-xs text-slate-400 font-mono">
            Showing <strong className="text-white">{filteredExceptions.length}</strong> exceptions
          </div>

          {paginatedExceptions.map((exc) => {
            const isInvestigating = investigatingIds[exc.exception_id];
            const invResult = investigations[exc.exception_id];
            const isExpanded = expandedIds[exc.exception_id];

            return (
              <div
                key={exc.exception_id}
                className="bg-slate-900 border border-slate-800 rounded-lg shadow-md overflow-hidden transition"
              >
                {/* Exception Card Header */}
                <div className="p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-900">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-bold text-blue-400">
                        {exc.exception_id}
                      </span>
                      <span className="font-mono text-xs text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                        TX: {exc.transaction_id}
                      </span>
                      <SeverityBadge severity={exc.severity} />
                      <StatusBadge status={exc.review_status} size="sm" />
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-300">
                      <div>
                        <span className="text-slate-500">Classification: </span>
                        <span className="font-mono text-slate-200 font-semibold">
                          {exc.exception_type}
                        </span>
                      </div>
                      {exc.difference !== null && (
                        <div>
                          <span className="text-slate-500">Difference: </span>
                          <span className="font-mono font-bold text-rose-400 tabular-nums">
                            {formatCurrency(exc.difference)}
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-slate-500">Suggested: </span>
                        <span className="font-mono text-emerald-300 font-semibold">
                          {exc.recommended_action}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions Toolbar */}
                  <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => setDrawerTxnId(exc.transaction_id)}
                      className="px-3 py-1.5 rounded bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-medium transition flex items-center gap-1.5"
                    >
                      <Scale className="w-3.5 h-3.5 text-blue-400" />
                      <span>3-Way Evidence</span>
                    </button>

                    <button
                      onClick={() => handleInvestigate(exc.exception_id)}
                      disabled={isInvestigating}
                      className="px-3 py-1.5 rounded bg-purple-950/80 hover:bg-purple-900 text-purple-300 border border-purple-700/80 text-xs font-medium transition flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {isInvestigating ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-300" />
                      ) : (
                        <BrainCircuit className="w-3.5 h-3.5 text-purple-400" />
                      )}
                      <span>{invResult ? 'Re-Investigate AI' : 'Investigate with AI'}</span>
                    </button>

                    <button
                      onClick={() => setActiveReviewException(exc)}
                      className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-sm"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Human Review</span>
                    </button>

                    <button
                      onClick={() => toggleExpand(exc.exception_id)}
                      className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      title="Toggle 3-Way Evidence & Investigation"
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded Section: 3-Way Parity, Lineage Pipeline, AI Card & Review History */}
                {isExpanded && (
                  <div className="border-t border-slate-800 p-4 bg-slate-950 space-y-4">
                    {/* 3-Way Financial Parity Comparison */}
                    <ThreeWayEvidenceVisualizer
                      transactionId={exc.transaction_id}
                      sourceRecords={exc.transaction?.source_records}
                      normalizedValues={exc.transaction?.normalized_values}
                      exceptionType={exc.exception_type}
                      difference={exc.difference}
                    />

                    {/* Decision Lineage Pipeline */}
                    <InvestigationPipeline
                      currentStage={
                        exc.review_status !== 'PENDING'
                          ? 'review'
                          : invResult
                          ? 'ai'
                          : 'deterministic'
                      }
                      exceptionType={exc.exception_type}
                      variance={exc.difference}
                      aiStatus={invResult ? invResult.investigation_status : isInvestigating ? 'Investigating...' : null}
                      reviewStatus={exc.review_status}
                    />
                    {/* Render AI Investigation Error if unconfigured/failed */}
                    {investigationErrors[exc.exception_id] && (() => {
                      const errMsg = investigationErrors[exc.exception_id];
                      const isUnconfigured = errMsg.toLowerCase().includes('unconfigured') || errMsg.toLowerCase().includes('not found in the environment');
                      return (
                        <div className={`rounded-lg border p-4 text-xs flex items-start gap-3 shadow-md ${
                          isUnconfigured ? 'border-amber-800 bg-amber-950/40 text-amber-200' : 'border-rose-800 bg-rose-950/40 text-rose-200'
                        }`}>
                          <AlertTriangle className={`w-5 h-5 shrink-0 mt-0.5 ${isUnconfigured ? 'text-amber-400' : 'text-rose-400'}`} />
                          <div className="space-y-1.5 flex-1">
                            <div className="flex items-center justify-between">
                              <p className="font-semibold text-slate-100">
                                {isUnconfigured ? 'Live AI Provider Not Configured' : 'Live AI Provider Temporary Outage'}
                              </p>
                              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                                isUnconfigured 
                                  ? 'bg-amber-900/60 border-amber-700 text-amber-300' 
                                  : 'bg-rose-900/60 border-rose-700 text-rose-300'
                              }`}>
                                Production Strict AI Enforcement
                              </span>
                            </div>
                            <p className="font-mono text-[11px] opacity-95">{errMsg}</p>
                            <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
                              {isUnconfigured 
                                ? 'To run real AI investigations, configure GEMINI_API_KEY or OPENAI_API_KEY in the server environment. The system strictly refuses to generate mock or fake responses.'
                                : 'The upstream AI model returned a temporary service error (503/429). The system has automatic model failover configured. Please click "Investigate with AI" to retry.'}
                            </p>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Render AI Result if available */}
                    {invResult && <AIInvestigationCard investigation={invResult} />}

                    {/* Render Review History if any */}
                    {exc.review_history && exc.review_history.length > 0 && (
                      <div className="bg-slate-900 rounded-lg p-4 border border-slate-855">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
                          <History className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Review Governance Audit Trail</span>
                        </h4>
                        <div className="space-y-2">
                          {exc.review_history.map((rev, rIdx) => (
                            <div
                              key={rIdx}
                              className="text-xs bg-slate-950 p-2.5 rounded border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                            >
                              <div className="flex items-center gap-2 font-mono">
                                <StatusBadge status={rev.previous_state} size="sm" />
                                <span className="text-slate-500">→</span>
                                <StatusBadge status={rev.new_state} size="sm" />
                                <span className="text-slate-400 ml-2">by</span>
                                <span className="text-white font-semibold">{rev.reviewer}</span>
                              </div>
                              <div className="text-slate-400 text-[11px] font-mono">
                                {rev.timestamp ? new Date(rev.timestamp).toLocaleString() : ''}
                              </div>
                              {rev.comment && (
                                <div className="text-slate-300 italic text-xs w-full pt-1 border-t border-slate-855">
                                  "{rev.comment}"
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Pagination Controls */}
          {filteredExceptions.length > pageSize && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span>Rows per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
                <span className="text-slate-500 ml-2">
                  Showing {(currentPage - 1) * pageSize + 1} -{' '}
                  {Math.min(currentPage * pageSize, filteredExceptions.length)} of{' '}
                  {filteredExceptions.length}
                </span>
              </div>
              <div className="flex items-center gap-2 self-end sm:self-auto">
                <span className="text-slate-300">
                  Page {currentPage} of {totalPages}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-1 rounded bg-slate-950 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                    title="Previous Page"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1 rounded bg-slate-950 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                    title="Next Page"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Review Action Modal */}
      {activeReviewException && (
        <ReviewActionModal
          exception={activeReviewException}
          isOpen={!!activeReviewException}
          onClose={() => setActiveReviewException(null)}
          onSuccess={handleReviewSuccess}
        />
      )}

      {/* 3-Way Transaction Detail Drawer */}
      <TransactionDetailDrawer
        transactionId={drawerTxnId}
        isOpen={!!drawerTxnId}
        onClose={() => setDrawerTxnId(null)}
      />
    </div>
  );
};
