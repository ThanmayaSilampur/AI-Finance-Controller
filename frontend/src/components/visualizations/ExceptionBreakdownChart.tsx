import React from 'react';
import { CheckCircle2, BarChart3 } from 'lucide-react';

interface ExceptionBreakdownChartProps {
  exceptionBreakdown: Record<string, number>;
  totalExceptions?: number;
  title?: string;
  subtitle?: string;
}

// Friendly formatting for system classification keys
const formatClassificationName = (key: string): string => {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

// Color palettes based on classification type
const getClassificationColor = (key: string): { bar: string; text: string; bg: string; border: string } => {
  const lower = key.toLowerCase();
  if (lower.includes('amount')) {
    return {
      bar: 'bg-rose-500',
      text: 'text-rose-400',
      bg: 'bg-rose-950/40',
      border: 'border-rose-900/40',
    };
  }
  if (lower.includes('missing')) {
    return {
      bar: 'bg-purple-500',
      text: 'text-purple-400',
      bg: 'bg-purple-950/40',
      border: 'border-purple-900/40',
    };
  }
  if (lower.includes('status')) {
    return {
      bar: 'bg-amber-500',
      text: 'text-amber-400',
      bg: 'bg-amber-950/40',
      border: 'border-amber-900/40',
    };
  }
  if (lower.includes('date')) {
    return {
      bar: 'bg-cyan-500',
      text: 'text-cyan-400',
      bg: 'bg-cyan-950/40',
      border: 'border-cyan-900/40',
    };
  }
  return {
    bar: 'bg-blue-500',
    text: 'text-blue-400',
    bg: 'bg-blue-950/40',
    border: 'border-blue-900/40',
  };
};

export const ExceptionBreakdownChart: React.FC<ExceptionBreakdownChartProps> = ({
  exceptionBreakdown,
  totalExceptions: explicitTotalExceptions,
  title = 'Exception Classification Breakdown',
  subtitle = 'Distribution by deterministic rule classification',
}) => {
  // Filter out any 0 count items and sort descending by count
  const sortedEntries = Object.entries(exceptionBreakdown || {})
    .filter(([_, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]);

  const total =
    explicitTotalExceptions !== undefined
      ? explicitTotalExceptions
      : sortedEntries.reduce((sum, [_, count]) => sum + count, 0);

  const maxCount = sortedEntries.length > 0 ? Math.max(...sortedEntries.map(([_, c]) => c)) : 1;

  if (sortedEntries.length === 0 || total === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 text-center space-y-2 shadow-md">
        <div className="w-10 h-10 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-400 flex items-center justify-center mx-auto mb-2">
          <CheckCircle2 className="w-5 h-5" />
        </div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">{title}</h3>
        <p className="text-xs text-emerald-400 font-mono">No exceptions identified in this analysis run.</p>
        <p className="text-[11px] text-slate-500">All ingested records passed 3-way reconciliation verification.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4 shadow-md">
      {/* Header */}
      <div className="border-b border-slate-800/80 pb-3 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <span>{title}</span>
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-900/60">
          Total Exceptions: <strong className="text-rose-200">{total}</strong>
        </span>
      </div>

      {/* Horizontal Bars */}
      <div className="space-y-3 pt-1">
        {sortedEntries.map(([category, count]) => {
          const percentage = total > 0 ? (count / total) * 100 : 0;
          const relativeWidthPct = (count / maxCount) * 100;
          const colors = getClassificationColor(category);

          return (
            <div key={category} className="space-y-1.5">
              {/* Category Label & Metrics */}
              <div className="flex items-center justify-between text-xs font-mono">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${colors.bar}`} />
                  <span className="text-slate-200 font-medium" title={category}>
                    {formatClassificationName(category)}
                  </span>
                  <span className="text-[10px] text-slate-500 font-sans">
                    ({category})
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-bold text-white font-mono">{count}</span>
                  <span className="text-[11px] text-slate-400 font-mono w-14 text-right">
                    {percentage.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Progress Bar Track & Fill */}
              <div className="h-2.5 w-full bg-slate-950 rounded-full overflow-hidden border border-slate-850 flex">
                <div
                  className={`h-full rounded-full ${colors.bar} transition-all duration-500 ease-out`}
                  style={{ width: `${Math.max(relativeWidthPct, 2)}%` }}
                  title={`${formatClassificationName(category)}: ${count} (${percentage.toFixed(1)}%)`}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Footer */}
      <div className="border-t border-slate-800/80 pt-3 flex items-center justify-between text-[11px] font-mono text-slate-500">
        <span>{sortedEntries.length} active classification category{sortedEntries.length > 1 ? 's' : ''}</span>
        <span>Sorted by occurrence count (descending)</span>
      </div>
    </div>
  );
};
