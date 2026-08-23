import React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
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
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  if (norm === 'MATCHED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 ${sizeClasses}`}>
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        MATCHED
      </span>
    );
  }

  if (norm === 'EXCEPTION') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-rose-950/80 text-rose-300 border border-rose-800/80 ${sizeClasses}`}>
        <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
        EXCEPTION
      </span>
    );
  }

  if (norm === 'PENDING') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-amber-950/80 text-amber-300 border border-amber-800/80 ${sizeClasses}`}>
        <Clock className="w-3.5 h-3.5 text-amber-400" />
        PENDING REVIEW
      </span>
    );
  }

  if (norm === 'APPROVED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-emerald-950/80 text-emerald-300 border border-emerald-700 ${sizeClasses}`}>
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        APPROVED
      </span>
    );
  }

  if (norm === 'REJECTED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-red-950/80 text-red-300 border border-red-800 ${sizeClasses}`}>
        <XCircle className="w-3.5 h-3.5 text-red-400" />
        REJECTED
      </span>
    );
  }

  if (norm === 'ESCALATED') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-purple-950/80 text-purple-300 border border-purple-800 ${sizeClasses}`}>
        <ArrowUpRight className="w-3.5 h-3.5 text-purple-400" />
        ESCALATED
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1 font-medium rounded-md bg-slate-800 text-slate-300 border border-slate-700 ${sizeClasses}`}>
      {norm}
    </span>
  );
};
