import React from 'react';
import {
  XCircle,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';
import { ReviewStatus } from '../api/types';

interface StatusBadgeProps {
  status: string | ReviewStatus | null | undefined;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const norm = (status || 'UNKNOWN').toUpperCase();
  const padding = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  if (norm === 'MATCHED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${padding}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        <span>Matched</span>
      </span>
    );
  }

  if (norm === 'EXCEPTION') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 ${padding}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
        <span>Exception</span>
      </span>
    );
  }

  if (norm === 'PENDING' || norm === 'PENDING REVIEW') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 ${padding}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        <span>Pending Review</span>
      </span>
    );
  }

  if (norm === 'APPROVED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${padding}`}>
        <ShieldCheck className="w-3 h-3 text-emerald-400" />
        <span>Approved</span>
      </span>
    );
  }

  if (norm === 'REJECTED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-red-500/10 text-red-400 border border-red-500/30 ${padding}`}>
        <XCircle className="w-3 h-3 text-red-400" />
        <span>Rejected</span>
      </span>
    );
  }

  if (norm === 'ESCALATED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30 ${padding}`}>
        <ArrowUpRight className="w-3 h-3 text-purple-400" />
        <span>Escalated</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-500/10 text-slate-400 border border-slate-700/50 ${padding}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
      <span>{norm}</span>
    </span>
  );
};
