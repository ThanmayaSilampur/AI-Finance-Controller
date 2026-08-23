import React from 'react';
import {
  Clock,
  ShieldCheck,
  BrainCircuit,
  ArrowRight,
  UserCheck,
  MessageSquare,
} from 'lucide-react';
import { RawAuditRecord, ReviewHistoryItem, InvestigationSummaryItem } from '../api/types';
import { StatusBadge } from './StatusBadge';

interface AuditTimelineProps {
  auditRecords?: RawAuditRecord[];
  reviewActions?: ReviewHistoryItem[];
  investigations?: InvestigationSummaryItem[];
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({
  auditRecords = [],
  reviewActions = [],
  investigations = [],
}) => {
  const hasItems =
    auditRecords.length > 0 || reviewActions.length > 0 || investigations.length > 0;

  if (!hasItems) {
    return (
      <div className="text-center py-8 text-slate-500 text-xs italic bg-slate-900/50 rounded-lg border border-slate-800">
        No audit lifecycle events recorded for this entity.
      </div>
    );
  }

  return (
    <div className="space-y-6 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
      {/* 1. Ingestion & Deterministic Seed Records */}
      {auditRecords.map((rec, idx) => (
        <div key={`audit-${idx}`} className="relative flex items-start gap-4 pl-1">
          <div className="w-6 h-6 rounded-full bg-blue-950 border border-blue-600 text-blue-400 flex items-center justify-center flex-shrink-0 z-10">
            <Clock className="w-3.5 h-3.5" />
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex-1 text-xs space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white">Reconciliation Seed & Audit Init</span>
                <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-blue-300">
                  {rec.audit_id}
                </span>
              </div>
              <span className="font-mono text-slate-500 text-[11px]">
                {rec.processing_timestamp ? new Date(rec.processing_timestamp).toLocaleString() : 'N/A'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
              <div>
                <span className="text-slate-500 block">Match Status:</span>
                <span className="text-rose-400 font-semibold">{rec.match_status}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Exception Type:</span>
                <span className="text-slate-300">{rec.exception_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Discrepancy:</span>
                <span className="text-slate-300">
                  {rec.difference !== null ? `₹${rec.difference.toFixed(2)}` : 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Initial State:</span>
                <span className="text-amber-400 font-semibold">{rec.review_status}</span>
              </div>
            </div>
          </div>
        </div>
      ))}

      {/* 2. AI Investigation Events */}
      {investigations.map((inv, idx) => (
        <div key={`inv-${idx}`} className="relative flex items-start gap-4 pl-1">
          <div className="w-6 h-6 rounded-full bg-purple-950 border border-purple-600 text-purple-400 flex items-center justify-center flex-shrink-0 z-10">
            <BrainCircuit className="w-3.5 h-3.5" />
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex-1 text-xs space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-purple-300">AI Advisory Investigation</span>
                <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                  {inv.investigation_id}
                </span>
              </div>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {inv.status}
              </span>
            </div>
            <p className="text-slate-300 italic bg-slate-950 p-2.5 rounded border border-slate-850">
              "{inv.summary}"
            </p>
          </div>
        </div>
      ))}

      {/* 3. Human Review Actions */}
      {reviewActions.map((rev, idx) => (
        <div key={`rev-${idx}`} className="relative flex items-start gap-4 pl-1">
          <div className="w-6 h-6 rounded-full bg-emerald-950 border border-emerald-500 text-emerald-400 flex items-center justify-center flex-shrink-0 z-10">
            <ShieldCheck className="w-3.5 h-3.5" />
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex-1 text-xs space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-emerald-300">Human Governance Review</span>
                <div className="flex items-center gap-1 font-mono text-[11px]">
                  <StatusBadge status={rev.previous_state} size="sm" />
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <StatusBadge status={rev.new_state} size="sm" />
                </div>
              </div>
              <span className="font-mono text-slate-500 text-[11px]">
                {rev.timestamp ? new Date(rev.timestamp).toLocaleString() : 'N/A'}
              </span>
            </div>

            <div className="flex items-center gap-2 text-slate-300 font-mono text-[11px]">
              <UserCheck className="w-3.5 h-3.5 text-blue-400" />
              <span>Reviewer:</span>
              <span className="text-white font-semibold">{rev.reviewer}</span>
            </div>

            {rev.comment && (
              <div className="bg-slate-950 p-2.5 rounded border border-slate-850 text-slate-300 flex items-start gap-2">
                <MessageSquare className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
                <span>{rev.comment}</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
