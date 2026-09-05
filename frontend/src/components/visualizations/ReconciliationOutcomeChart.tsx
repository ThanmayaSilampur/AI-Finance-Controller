import React from 'react';
import { CheckCircle2, AlertTriangle, Scale } from 'lucide-react';

interface ReconciliationOutcomeChartProps {
  totalRecords: number;
  matchedCount: number;
  exceptionCount: number;
  matchRate?: number;
  title?: string;
}

export const ReconciliationOutcomeChart: React.FC<ReconciliationOutcomeChartProps> = ({
  totalRecords,
  matchedCount,
  exceptionCount,
  matchRate: explicitMatchRate,
  title = 'Reconciliation Outcome',
}) => {
  if (totalRecords === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 text-center space-y-3">
        <Scale className="w-8 h-8 text-slate-600 mx-auto" />
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
        <p className="text-xs text-slate-500 font-mono">No analysis records available in this run.</p>
      </div>
    );
  }

  // Calculate percentages safely from actual backend numbers
  const calculatedMatchRate = totalRecords > 0 ? (matchedCount / totalRecords) * 100 : 0;
  const matchPct = explicitMatchRate !== undefined ? explicitMatchRate : calculatedMatchRate;
  const exceptionPct = totalRecords > 0 ? (exceptionCount / totalRecords) * 100 : 0;

  // SVG Donut metrics
  const size = 140;
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Dash offsets
  // Segment 1: Matched (emerald)
  const matchedOffset = 0;
  const matchedDash = (matchPct / 100) * circumference;

  // Segment 2: Exceptions (rose)
  const exceptionDash = (exceptionPct / 100) * circumference;
  const exceptionOffset = -matchedDash;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between shadow-md">
      {/* Header */}
      <div className="border-b border-slate-800/80 pb-3 mb-4 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-white flex items-center gap-2">
          <Scale className="w-4 h-4 text-blue-400" />
          <span>{title}</span>
        </h3>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
          Total: <strong className="text-white">{totalRecords}</strong>
        </span>
      </div>

      {/* Visualization Body */}
      <div className="flex flex-col sm:flex-row items-center justify-around gap-6 py-2">
        {/* SVG Donut */}
        <div className="relative flex-shrink-0 flex items-center justify-center">
          <svg
            width={size}
            height={size}
            className="transform -rotate-90"
            viewBox={`0 0 ${size} ${size}`}
            aria-label={`Donut chart showing ${matchPct.toFixed(1)}% matched and ${exceptionPct.toFixed(1)}% exceptions`}
            role="img"
          >
            {/* Background ring track */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke="currentColor"
              className="text-slate-800"
              strokeWidth={strokeWidth}
            />

            {/* Matched ring (emerald) */}
            {matchedCount > 0 && (
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="transparent"
                stroke="#10b981"
                strokeWidth={strokeWidth}
                strokeDasharray={`${matchedDash} ${circumference}`}
                strokeDashoffset={matchedOffset}
                strokeLinecap="round"
                className="transition-all duration-500 ease-out"
              />
            )}

            {/* Exception ring (rose) */}
            {exceptionCount > 0 && (
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="transparent"
                stroke="#f43f5e"
                strokeWidth={strokeWidth}
                strokeDasharray={`${exceptionDash} ${circumference}`}
                strokeDashoffset={exceptionOffset}
                strokeLinecap="round"
                className="transition-all duration-500 ease-out"
              />
            )}
          </svg>

          {/* Center Callout */}
          <div className="absolute flex flex-col items-center justify-center text-center pointer-events-none">
            <span className="text-2xl font-bold font-mono text-white tracking-tight">
              {matchPct.toFixed(1)}%
            </span>
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              Match Rate
            </span>
          </div>
        </div>

        {/* Legend & Exact Numerical Breakdown */}
        <div className="flex-1 w-full space-y-3 font-mono text-xs">
          {/* Matched row */}
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-850 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500 flex-shrink-0" />
              <div className="flex flex-col">
                <span className="text-slate-200 font-semibold flex items-center gap-1">
                  <span>Matched Records</span>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                </span>
                <span className="text-[10px] text-slate-500 font-sans">Full 3-way parity verified</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-base font-bold text-emerald-400">{matchedCount}</div>
              <div className="text-[10px] text-slate-400">{matchPct.toFixed(1)}%</div>
            </div>
          </div>

          {/* Exception row */}
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-850 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500 flex-shrink-0" />
              <div className="flex flex-col">
                <span className="text-slate-200 font-semibold flex items-center gap-1">
                  <span>Exception Records</span>
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                </span>
                <span className="text-[10px] text-slate-500 font-sans">Requires triage & investigation</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-base font-bold text-rose-400">{exceptionCount}</div>
              <div className="text-[10px] text-slate-400">{exceptionPct.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
