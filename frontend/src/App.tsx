import React, { useState, useEffect } from 'react';
import { Header, NavTab } from './components/Header';
import { DashboardView } from './views/DashboardView';
import { ReconciliationView } from './views/ReconciliationView';
import { ExceptionsView } from './views/ExceptionsView';
import { AuditView } from './views/AuditView';
import { ReportsView } from './views/ReportsView';
import { NewAnalysisView } from './views/NewAnalysisView';
import { FinanceCopilotDrawer } from './components/FinanceCopilotDrawer';
import { api } from './api/client';
import { AnalysisBatch } from './api/types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [reconStatusFilter, setReconStatusFilter] = useState<string>('ALL');
  const [exceptionStatusFilter, setExceptionStatusFilter] = useState<string>('ALL');
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null);
  const [auditTransactionId, setAuditTransactionId] = useState<string | null>(null);
  const [isCopilotOpen, setIsCopilotOpen] = useState<boolean>(false);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('finance_theme');
    return saved === 'light' || saved === 'dark' ? saved : 'dark';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'light') {
      root.classList.add('light');
      root.classList.remove('dark');
    } else {
      root.classList.add('dark');
      root.classList.remove('light');
    }
    localStorage.setItem('finance_theme', theme);
  }, [theme]);

  const [batches, setBatches] = useState<AnalysisBatch[]>([]);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);

  const [pendingCount, setPendingCount] = useState<number>(0);
  const [exceptionCount, setExceptionCount] = useState<number>(0);

  const loadBatches = async () => {
    try {
      const data = await api.getBatches();
      setBatches(data);
      if (data.length > 0 && !activeBatchId) {
        setActiveBatchId(data[0].batch_id);
      }
    } catch {
      // Ignored for initial loading
    }
  };

  const loadHeaderMetrics = async () => {
    try {
      const [exceptions, report] = await Promise.all([
        api.getExceptions({ review_status: 'PENDING', batch_id: activeBatchId || undefined }),
        api.getReconciliationReport(activeBatchId || undefined),
      ]);
      setPendingCount(exceptions.length);
      setExceptionCount(report.unresolved);
    } catch {
      // Handled silently for background badge updates
    }
  };

  useEffect(() => {
    loadBatches();
  }, []);

  useEffect(() => {
    loadHeaderMetrics();
    const interval = setInterval(() => {
      if (typeof document === 'undefined' || document.visibilityState === 'visible') {
        loadHeaderMetrics();
      }
    }, 15000);
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        loadHeaderMetrics();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [activeBatchId]);

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

  const handleBatchCreated = (batch: AnalysisBatch) => {
    setBatches((prev) => [batch, ...prev.filter((b) => b.batch_id !== batch.batch_id)]);
    setActiveBatchId(batch.batch_id);
    setActiveTab('dashboard');
  };

  return (
    <div className={`min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans ${theme}`}>
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        exceptionCount={exceptionCount}
        pendingReviewCount={pendingCount}
        batches={batches}
        activeBatchId={activeBatchId}
        onSelectBatch={(id) => setActiveBatchId(id)}
        onToggleCopilot={() => setIsCopilotOpen((prev) => !prev)}
        theme={theme}
        onToggleTheme={(newTheme) => setTheme(newTheme)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <DashboardView
            activeBatchId={activeBatchId}
            onNavigateToExceptions={handleNavigateToExceptions}
            onNavigateToReconciliation={handleNavigateToReconciliation}
            onSelectTransaction={handleSelectTransaction}
            onNavigateToUpload={() => setActiveTab('upload')}
          />
        )}

        {activeTab === 'reconciliation' && (
          <ReconciliationView
            activeBatchId={activeBatchId}
            initialStatusFilter={reconStatusFilter}
            selectedTransactionId={selectedTransactionId}
            onClearSelectedTransaction={() => setSelectedTransactionId(null)}
          />
        )}

        {activeTab === 'exceptions' && (
          <ExceptionsView
            activeBatchId={activeBatchId}
            initialStatusFilter={exceptionStatusFilter}
            onNavigateToAudit={handleNavigateToAudit}
          />
        )}

        {activeTab === 'audit' && (
          <AuditView
            initialTransactionId={auditTransactionId}
            activeBatchId={activeBatchId}
          />
        )}

        {activeTab === 'reports' && (
          <ReportsView activeBatchId={activeBatchId} />
        )}

        {activeTab === 'upload' && (
          <NewAnalysisView
            onAnalysisComplete={handleBatchCreated}
            onCancel={() => setActiveTab('dashboard')}
          />
        )}
      </main>

      {/* AI Finance Copilot Drawer */}
      <FinanceCopilotDrawer
        isOpen={isCopilotOpen}
        onClose={() => setIsCopilotOpen(false)}
        activeBatchId={activeBatchId}
        onSelectTransaction={handleSelectTransaction}
      />

      {/* Controller Footer */}
      <footer className="bg-slate-900 border-t border-slate-800/80 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500 font-mono">
          <div>
            AI Finance Controller
          </div>
          <div className="text-[11px] text-slate-500">
            Institutional Finance Operations
          </div>
        </div>
      </footer>
    </div>
  );
};
