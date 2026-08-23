import React, { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  Scale,
  AlertTriangle,
  FileText,
  History,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';

export type NavTab = 'dashboard' | 'reconciliation' | 'exceptions' | 'audit' | 'reports';

interface HeaderProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  exceptionCount?: number;
  pendingReviewCount?: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onSelectTab,
  pendingReviewCount = 0,
}) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(false);

  const checkHealth = async () => {
    try {
      setIsCheckingHealth(true);
      const res = await api.getHealth();
      setIsHealthy(res.status === 'ok');
      setIsCheckingHealth(false);
    } catch {
      setIsHealthy(false);
      setIsCheckingHealth(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

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
              <div className="flex items-center gap-2">
                <span className="font-bold tracking-tight text-white text-sm">
                  AI FINANCE CONTROLLER
                </span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                  Stage 10 UI
                </span>
              </div>
              <span className="text-[11px] text-slate-400 block -mt-0.5 hidden sm:block">
                3-Way Reconciliation & Governance Console
              </span>
            </div>
          </div>

          {/* Backend Health Status Monitor */}
          <div className="flex items-center gap-3">
            <button
              onClick={checkHealth}
              disabled={isCheckingHealth}
              title="Click to re-check API status"
              className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 text-xs text-slate-300 hover:border-slate-700 transition"
            >
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isHealthy === true
                      ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50'
                      : isHealthy === false
                      ? 'bg-rose-500 animate-ping'
                      : 'bg-amber-500'
                  }`}
                />
                <span className="font-mono text-[11px]">
                  {isHealthy === true
                    ? 'API ONLINE'
                    : isHealthy === false
                    ? 'API DISCONNECTED'
                    : 'CONNECTING...'}
                </span>
              </div>
              <RefreshCw className={`w-3 h-3 text-slate-500 ${isCheckingHealth ? 'animate-spin' : ''}`} />
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
