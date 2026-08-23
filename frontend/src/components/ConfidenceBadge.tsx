import React from 'react';
import { AlertCircle, CheckCircle2, HelpCircle } from 'lucide-react';
import { ConfidenceLevel } from '../api/types';

interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel | string | null | undefined;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence }) => {
  const norm = (confidence || 'LOW').toUpperCase();

  if (norm === 'HIGH') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-950/90 text-emerald-300 border border-emerald-700">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        HIGH CONFIDENCE
      </span>
    );
  }

  if (norm === 'MEDIUM') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-sky-950/90 text-sky-300 border border-sky-700">
        <HelpCircle className="w-3.5 h-3.5 text-sky-400" />
        MEDIUM CONFIDENCE
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-amber-950/90 text-amber-300 border border-amber-600 animate-pulse">
      <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
      LOW CONFIDENCE — INSUFFICIENT EVIDENCE
    </span>
  );
};
