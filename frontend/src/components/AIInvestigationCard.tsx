import React from 'react';
import {
  BrainCircuit,
  AlertTriangle,
  FileSearch,
  CheckCheck,
  HelpCircle,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';
import { InvestigationResponse } from '../api/types';
import { ConfidenceBadge } from './ConfidenceBadge';

interface AIInvestigationCardProps {
  investigation: InvestigationResponse;
}

export const AIInvestigationCard: React.FC<AIInvestigationCardProps> = ({ investigation }) => {
  const isLowConfidence = investigation.confidence === 'LOW';

  return (
    <div className="rounded-lg border border-blue-900/60 bg-slate-900/90 shadow-xl overflow-hidden text-slate-200">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-blue-950 via-slate-900 to-indigo-950 px-5 py-4 border-b border-blue-800/40 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-md bg-blue-600/20 border border-blue-500/30 text-blue-400">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-white tracking-wide text-sm">
                AI ROOT-CAUSE INVESTIGATION
              </h3>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-300 font-mono border border-blue-800">
                {investigation.investigation_id}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Read-only advisory analysis • Deterministic backend reconciliation is authoritative
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
            Status: {investigation.investigation_status}
          </span>
          <ConfidenceBadge confidence={investigation.confidence} />
        </div>
      </div>

      {/* Low Confidence / Insufficient Evidence Warning Banner */}
      {isLowConfidence && (
        <div className="bg-amber-950/80 border-b border-amber-800/60 px-5 py-3 flex items-start gap-3 text-amber-200 text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-semibold text-amber-300">INSUFFICIENT EVIDENCE DETECTED:</span>{' '}
            The AI investigation could not find sufficient historical corroboration or rule patterns to reliably explain this discrepancy.
            Do <span className="underline font-bold">NOT</span> treat tentative causes as verified accounting facts. Full human investigation is mandatory.
          </div>
        </div>
      )}

      <div className="p-5 space-y-5">
        {/* Executive Summary */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
            <FileSearch className="w-3.5 h-3.5 text-blue-400" />
            Executive Summary
          </h4>
          <p className="text-sm bg-slate-950 p-3 rounded-md border border-slate-800 font-sans text-slate-200 leading-relaxed">
            {investigation.summary || 'No summary generated.'}
          </p>
        </div>

        {/* Findings List */}
        {investigation.findings && investigation.findings.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
              <CheckCheck className="w-3.5 h-3.5 text-emerald-400" />
              Observed Findings
            </h4>
            <ul className="space-y-1.5">
              {investigation.findings.map((finding, idx) => (
                <li
                  key={idx}
                  className="text-xs bg-slate-950/70 p-2.5 rounded border border-slate-800/80 flex items-start gap-2 text-slate-300"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Evidence Breakdown */}
        {investigation.evidence && Object.keys(investigation.evidence).length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Evidence Evaluated
            </h4>
            <div className="bg-slate-950 rounded-md border border-slate-800 p-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              {investigation.evidence.payment_amount !== undefined && (
                <div>
                  <span className="text-slate-500 block text-[11px]">Payment Amount</span>
                  <span className="text-slate-200 font-semibold">
                    {investigation.evidence.payment_amount !== null
                      ? `₹${investigation.evidence.payment_amount.toFixed(2)}`
                      : 'N/A'}
                  </span>
                </div>
              )}
              {investigation.evidence.bank_amount !== undefined && (
                <div>
                  <span className="text-slate-500 block text-[11px]">Bank Amount</span>
                  <span className="text-slate-200 font-semibold">
                    {investigation.evidence.bank_amount !== null
                      ? `₹${investigation.evidence.bank_amount.toFixed(2)}`
                      : 'N/A'}
                  </span>
                </div>
              )}
              {investigation.evidence.ledger_amount !== undefined && (
                <div>
                  <span className="text-slate-500 block text-[11px]">Ledger Amount</span>
                  <span className="text-slate-200 font-semibold">
                    {investigation.evidence.ledger_amount !== null
                      ? `₹${investigation.evidence.ledger_amount.toFixed(2)}`
                      : 'N/A'}
                  </span>
                </div>
              )}
              {investigation.evidence.difference !== undefined && (
                <div>
                  <span className="text-slate-500 block text-[11px]">Discrepancy</span>
                  <span className="text-rose-400 font-semibold">
                    {investigation.evidence.difference !== null
                      ? `₹${investigation.evidence.difference.toFixed(2)}`
                      : 'None'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Possible Causes Breakdown */}
        {investigation.possible_causes && investigation.possible_causes.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-purple-400" />
              Hypothesis & Root-Cause Analysis
            </h4>
            <div className="space-y-2">
              {investigation.possible_causes.map((pc, idx) => (
                <div
                  key={idx}
                  className="bg-slate-950 p-3 rounded-md border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200">{pc.cause}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${
                          pc.likelihood === 'HIGH'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : 'bg-slate-800 text-slate-300 border border-slate-700'
                        }`}
                      >
                        {pc.likelihood} LIKELIHOOD
                      </span>
                    </div>
                    <p className="text-slate-400 text-xs">{pc.reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Most Likely Cause & Recommended Action Footer */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
          <div className="bg-slate-950/80 p-3 rounded border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-1">
              Most Likely Cause
            </span>
            <span className={`text-sm font-semibold ${isLowConfidence ? 'text-amber-300' : 'text-blue-300'}`}>
              {investigation.most_likely_cause || 'UNKNOWN'}
            </span>
          </div>

          <div className="bg-slate-950/80 p-3 rounded border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-1 flex items-center gap-1">
              <ArrowRight className="w-3 h-3 text-blue-400" />
              Recommended Action
            </span>
            <span className="text-sm font-semibold text-emerald-300">
              {investigation.recommended_action || 'Manual investigation required.'}
            </span>
          </div>
        </div>

        {/* Human Governance Requirement */}
        <div className="flex items-center justify-between pt-1 text-xs text-slate-400">
          <span className="inline-flex items-center gap-1.5 text-amber-400 font-medium">
            <ShieldAlert className="w-4 h-4" />
            Human Review Required: {investigation.requires_human_review ? 'YES (Mandatory)' : 'Optional'}
          </span>
          <span className="text-slate-500 font-mono text-[11px]">
            Target Exception: {investigation.exception_id}
          </span>
        </div>
      </div>
    </div>
  );
};
