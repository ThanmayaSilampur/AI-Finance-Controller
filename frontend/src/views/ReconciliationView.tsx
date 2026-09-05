import React, { useEffect, useState, useMemo } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  Loader2,
  ExternalLink,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import { TransactionSummary } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { TransactionDetailDrawer } from '../components/TransactionDetailDrawer';

interface ReconciliationViewProps {
  activeBatchId?: string | null;
  initialStatusFilter?: string;
  selectedTransactionId?: string | null;
  onClearSelectedTransaction?: () => void;
}

export const ReconciliationView: React.FC<ReconciliationViewProps> = ({
  activeBatchId,
  initialStatusFilter,
  selectedTransactionId,
  onClearSelectedTransaction,
}) => {
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>(initialStatusFilter || 'ALL');
  const [exceptionTypeFilter, setExceptionTypeFilter] = useState<string>('ALL');

  // Drawer State
  const [drawerTxnId, setDrawerTxnId] = useState<string | null>(selectedTransactionId || null);

  useEffect(() => {
    if (selectedTransactionId) {
      setDrawerTxnId(selectedTransactionId);
    }
  }, [selectedTransactionId]);

  const loadTransactions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await api.getTransactions({
        batch_id: activeBatchId || undefined,
      });
      setTransactions(data);
      setIsLoading(false);
    } catch (err: any) {
      setIsLoading(false);
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to fetch reconciliation records.');
      } else {
        setError(err.message || 'Unable to connect to the Finance Controller API.');
      }
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [activeBatchId]);

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, statusFilter, exceptionTypeFilter, activeBatchId]);

  // Compute available exception types
  const availableExceptionTypes = useMemo(() => {
    const types = new Set<string>();
    transactions.forEach((tx) => {
      if (tx.exception_type) types.add(tx.exception_type);
    });
    return Array.from(types).sort();
  }, [transactions]);

  // Filtered transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter((tx) => {
      const matchesSearch =
        !searchQuery.trim() ||
        tx.transaction_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (tx.exception_type && tx.exception_type.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStatus =
        statusFilter === 'ALL' ||
        tx.status.toUpperCase() === statusFilter.toUpperCase();

      const matchesExceptionType =
        exceptionTypeFilter === 'ALL' ||
        tx.exception_type === exceptionTypeFilter;

      return matchesSearch && matchesStatus && matchesExceptionType;
    });
  }, [transactions, searchQuery, statusFilter, exceptionTypeFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredTransactions.length / pageSize));
  const paginatedTransactions = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredTransactions.slice(start, start + pageSize);
  }, [filteredTransactions, currentPage, pageSize]);

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Reconciliation Ledger</h1>
        </div>
        <button
          onClick={loadTransactions}
          className="self-start sm:self-auto inline-flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-md text-xs font-medium transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
          <span>Reload Ledger</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by Transaction ID or Rule..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
          >
            <option value="ALL">All Match Statuses</option>
            <option value="MATCHED">MATCHED Only</option>
            <option value="EXCEPTION">EXCEPTION Only</option>
          </select>
        </div>

        {/* Exception Type Filter */}
        <div>
          <select
            value={exceptionTypeFilter}
            onChange={(e) => setExceptionTypeFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
          >
            <option value="ALL">All Exception Classifications</option>
            {availableExceptionTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table Results */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="text-xs font-mono">Querying deterministic reconciliation ledger...</span>
        </div>
      ) : error ? (
        <div className="p-6 bg-slate-900 border border-rose-800 rounded-xl text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
          <p className="text-xs text-rose-300 font-mono">{error}</p>
          <button
            onClick={loadTransactions}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : filteredTransactions.length === 0 ? (
        <div className="py-16 text-center text-xs text-slate-400 bg-slate-900 rounded-lg border border-slate-800">
          No transactions matched the selected filter criteria.
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-lg">
          <div className="px-4 py-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>
              Showing <strong className="text-white">{filteredTransactions.length}</strong> of {transactions.length} records
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-mono text-[11px]">
                <tr>
                  <th className="px-4 py-3">Transaction ID</th>
                  <th className="px-4 py-3">Reconciliation Status</th>
                  <th className="px-4 py-3">Match Score</th>
                  <th className="px-4 py-3">Exception Classification</th>
                  <th className="px-4 py-3">Recommended Resolution</th>
                  <th className="px-4 py-3 text-right">3-Way Trace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-sans">
                {paginatedTransactions.map((tx) => (
                  <tr
                    key={tx.transaction_id}
                    className="hover:bg-slate-850/60 transition group cursor-pointer"
                    onClick={() => setDrawerTxnId(tx.transaction_id)}
                  >
                    <td className="px-4 py-3 font-mono font-semibold text-blue-400">
                      {tx.transaction_id}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={tx.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-mono">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full ${
                              tx.match_score >= 0.8
                                ? 'bg-emerald-500'
                                : tx.match_score >= 0.5
                                ? 'bg-amber-500'
                                : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.round(tx.match_score * 100)}%` }}
                          />
                        </div>
                        <span className="text-[11px] text-slate-300 font-semibold">
                          {(tx.match_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      {tx.exception_type ? (
                        <span className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800/80 text-[11px]">
                          {tx.exception_type}
                        </span>
                      ) : (
                        <span className="text-slate-500 text-[11px]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      <span className="text-slate-300">{tx.recommended_action}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDrawerTxnId(tx.transaction_id);
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-800 group-hover:bg-blue-600 text-slate-300 group-hover:text-white transition text-xs font-mono"
                      >
                        <span>Inspect</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {filteredTransactions.length > pageSize && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 border-t border-slate-800 bg-slate-950/60 text-xs font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span>Rows per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
                <span className="text-slate-500 ml-2">
                  Showing {(currentPage - 1) * pageSize + 1} -{' '}
                  {Math.min(currentPage * pageSize, filteredTransactions.length)} of{' '}
                  {filteredTransactions.length}
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
                    className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                    title="Previous Page"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
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

      {/* Drawer */}
      <TransactionDetailDrawer
        transactionId={drawerTxnId}
        isOpen={!!drawerTxnId}
        onClose={() => {
          setDrawerTxnId(null);
          if (onClearSelectedTransaction) onClearSelectedTransaction();
        }}
      />
    </div>
  );
};
