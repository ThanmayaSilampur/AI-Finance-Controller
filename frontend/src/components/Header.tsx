import React from 'react';
import {
  LayoutDashboard,
  Scale,
  AlertTriangle,
  FileText,
  History,
  UploadCloud,
  Layers,
} from 'lucide-react';
import { AnalysisBatch } from '../api/types';

export type NavTab = 'dashboard' | 'reconciliation' | 'exceptions' | 'audit' | 'reports' | 'upload';

interface HeaderProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  exceptionCount?: number;
  pendingReviewCount?: number;
  batches?: AnalysisBatch[];
  activeBatchId?: string | null;
  onSelectBatch?: (batchId: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onSelectTab,
  pendingReviewCount = 0,
  batches = [],
  activeBatchId,
  onSelectBatch,
}) => {
  const navItems: Array<{ id: NavTab; label: string; icon: React.ReactNode; badge?: number }> = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'reconciliation', label: 'Reconciliation', icon: <Scale className="w-4 h-4" /> },
    {
      id: 'exceptions',
      label: 'Exceptions Queue',
      icon: <AlertTriangle className="w-4 h-4" />,
      badge: pendingReviewCount > 0 ? pendingReviewCount : undefined,
    },
    { id: 'audit', label: 'Audit Trail', icon: <History className="w-4 h-4" /> },
    { id: 'reports', label: 'Reports & Export', icon: <FileText className="w-4 h-4" /> },
    { id: 'upload', label: 'New Analysis', icon: <UploadCloud className="w-4 h-4" /> },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & System Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-900/40 font-bold font-mono">
              ₹
            </div>
            <div>
              <span className="font-bold tracking-tight text-white text-sm block">
                AI FINANCE CONTROLLER
              </span>
              <span className="text-[11px] text-slate-400 block -mt-0.5 hidden sm:block">
                Dynamic Ingestion & 3-Way Reconciliation
              </span>
            </div>
          </div>

          {/* Current Analysis / Run Selector and + New Analysis */}
          <div className="flex items-center gap-3">
            {/* Batch Selector Dropdown or Empty State */}
            {batches.length > 0 && onSelectBatch ? (
              <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 rounded-md px-2.5 py-1 text-xs text-slate-300">
                <Layers className="w-3.5 h-3.5 text-blue-400" />
                <select
                  value={activeBatchId || ''}
                  onChange={(e) => onSelectBatch(e.target.value)}
                  className="bg-transparent text-slate-200 text-xs font-mono focus:outline-none cursor-pointer"
                >
                  {batches.map((b) => (
                    <option key={b.batch_id} value={b.batch_id} className="bg-slate-900 text-slate-200">
                      {b.batch_name || b.batch_id} ({b.total_records} txns, {b.match_rate}% match)
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <button
                onClick={() => onSelectTab('upload')}
                className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-md px-2.5 py-1 text-xs text-slate-400"
              >
                <Layers className="w-3.5 h-3.5 text-slate-500" />
                <span className="font-mono text-[11px]">No Active Analysis</span>
              </button>
            )}

            {/* Quick New Analysis Button */}
            <button
              onClick={() => onSelectTab('upload')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition shadow-sm ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white'
                  : 'bg-blue-600/90 hover:bg-blue-600 text-white'
              }`}
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>+ New Analysis</span>
            </button>
          </div>
        </div>

        {/* Primary Navigation Tabs */}
        <nav className="flex space-x-1 border-t border-slate-800/80 overflow-x-auto py-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-md text-xs font-medium transition whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
                {item.badge !== undefined && (
                  <span
                    className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                      isActive ? 'bg-white text-blue-900' : 'bg-amber-500 text-slate-950'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
