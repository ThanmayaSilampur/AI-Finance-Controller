import React, { useState, useEffect } from 'react';
import { Header, NavTab } from './components/Header';
import { DashboardView } from './views/DashboardView';
import { ReconciliationView } from './views/ReconciliationView';
import { ExceptionsView } from './views/ExceptionsView';
import { AuditView } from './views/AuditView';
import { ReportsView } from './views/ReportsView';
import { api } from './api/client';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [reconStatusFilter, setReconStatusFilter] = useState<string>('ALL');
  const [exceptionStatusFilter, setExceptionStatusFilter] = useState<string>('ALL');
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null);
  const [auditTransactionId, setAuditTransactionId] = useState<string | null>(null);

  const [pendingCount, setPendingCount] = useState<number>(0);
  const [exceptionCount, setExceptionCount] = useState<number>(0);

  const loadHeaderMetrics = async () => {
    try {
      const [exceptions, report] = await Promise.all([
        api.getExceptions({ review_status: 'PENDING' }),
        api.getReconciliationReport(),
      ]);
      setPendingCount(exceptions.length);
      setExceptionCount(report.unresolved);
    } catch {
      // Handled silently for background badge updates
    }
  };

  useEffect(() => {
    loadHeaderMetrics();
    const interval = setInterval(loadHeaderMetrics, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleNavigateToExceptions = (statusFilter?: string) => {
    setExceptionStatusFilter(statusFilter || 'ALL');
    setActiveTab('exceptions');
  };

  const handleNavigateToReconciliation = (statusFilter?: string) => {
    setReconStatusFilter(statusFilter || 'ALL');
    setActiveTab('reconciliation');
  };

  const handleSelectTransaction = (transactionId: string) => {
    setSelectedTransactionId(transactionId);
    setActiveTab('reconciliation');
  };

  const handleNavigateToAudit = (transactionId: string) => {
    setAuditTransactionId(transactionId);
    setActiveTab('audit');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        exceptionCount={exceptionCount}
        pendingReviewCount={pendingCount}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <DashboardView
            onNavigateToExceptions={handleNavigateToExceptions}
            onNavigateToReconciliation={handleNavigateToReconciliation}
            onSelectTransaction={handleSelectTransaction}
          />
        )}

        {activeTab === 'reconciliation' && (
          <ReconciliationView
            initialStatusFilter={reconStatusFilter}
            selectedTransactionId={selectedTransactionId}
            onClearSelectedTransaction={() => setSelectedTransactionId(null)}
          />
        )}

        {activeTab === 'exceptions' && (
          <ExceptionsView
            initialStatusFilter={exceptionStatusFilter}
            onNavigateToAudit={handleNavigateToAudit}
          />
        )}

        {activeTab === 'audit' && (
          <AuditView initialTransactionId={auditTransactionId} />
        )}

        {activeTab === 'reports' && <ReportsView />}
      </main>

      {/* Controller Footer */}
      <footer className="bg-slate-900 border-t border-slate-800/80 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500 font-mono">
          <div>
            AI Finance Controller • Operational Stage 10 Frontend
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span>FastAPI Backend (Python 3.13)</span>
            <span>•</span>
            <span>Deterministic 3-Way Engine</span>
            <span>•</span>
            <span>Immutable Audit Store</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
