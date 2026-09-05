import React from 'react';
import { SeverityLevel } from '../api/types';

interface SeverityBadgeProps {
  severity: SeverityLevel | string | null | undefined;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const norm = (severity || 'LOW').toUpperCase();

  if (norm === 'HIGH' || norm === 'CRITICAL') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-semibold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
        <span>High Priority</span>
      </span>
    );
  }

  if (norm === 'MEDIUM') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        <span>Medium</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-semibold rounded-full bg-slate-500/10 text-slate-400 border border-slate-700/50">
      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
      <span>Low</span>
    </span>
  );
};
