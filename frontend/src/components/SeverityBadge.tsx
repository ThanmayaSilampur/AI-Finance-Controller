import React from 'react';
import { SeverityLevel } from '../api/types';

interface SeverityBadgeProps {
  severity: SeverityLevel | string | null | undefined;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const norm = (severity || 'LOW').toUpperCase();

  if (norm === 'HIGH') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded bg-rose-950 text-rose-300 border border-rose-800">
        HIGH PRIORITY
      </span>
    );
  }

  if (norm === 'MEDIUM') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded bg-amber-950 text-amber-300 border border-amber-800">
        MEDIUM
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded bg-slate-800 text-slate-300 border border-slate-700">
      LOW
    </span>
  );
};
