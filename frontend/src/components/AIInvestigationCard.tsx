import React from 'react';
import {
  BrainCircuit,
  AlertTriangle,
  FileSearch,
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
        {/* SECTION 1: SOURCE FACTS & EVIDENCE EVALUATED */}
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <FileSearch className="w-3.5 h-3.5 text-blue-400" />
              <span>Source Facts (Observed In Persisted Records)</span>
            </h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800">
              Deterministic Evidence
            </span>
          </div>

          {/* Evidence Grid */}
          {investigation.evidence && Object.keys(investigation.evidence).length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono pt-1">
              <div>
                <span className="text-slate-500 block text-[11px]">Payment Amount</span>
                <span className="text-slate-200 font-semibold">
                  {investigation.evidence.payment_amount !== null && investigation.evidence.payment_amount !== undefined
                    ? `₹${investigation.evidence.payment_amount.toFixed(2)}`
                    : <span className="text-rose-400">MISSING (None)</span>}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Bank Amount</span>
                <span className="text-slate-200 font-semibold">
                  {investigation.evidence.bank_amount !== null && investigation.evidence.bank_amount !== undefined
                    ? `₹${investigation.evidence.bank_amount.toFixed(2)}`
                    : <span className="text-rose-400">MISSING (None)</span>}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Ledger Amount</span>
                <span className="text-slate-200 font-semibold">
                  {investigation.evidence.ledger_amount !== null && investigation.evidence.ledger_amount !== undefined
                    ? `₹${investigation.evidence.ledger_amount.toFixed(2)}`
                    : <span className="text-rose-400">MISSING (None)</span>}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Discrepancy</span>
                <span className="font-semibold text-rose-400">
                  {investigation.evidence.difference !== null && investigation.evidence.difference !== undefined
                    ? `₹${investigation.evidence.difference.toFixed(2)}`
                    : 'None'}
                </span>
              </div>
            </div>
          )}

          {/* Missing Leg Indicators */}
          {investigation.evidence?.missing_legs && investigation.evidence.missing_legs.length > 0 && (
            <div className="pt-2 border-t border-slate-900 flex items-center gap-2 text-xs">
              <span className="text-slate-400 text-[11px]">Explicitly Missing Leg(s):</span>
              {investigation.evidence.missing_legs.map((leg: string) => (
                <span key={leg} className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 font-mono text-[10px] border border-rose-800">
                  {leg.toUpperCase()} STREAM MISSING
                </span>
              ))}
            </div>
          )}

          {/* Observed Findings list */}
          {investigation.findings && investigation.findings.length > 0 && (
            <ul className="space-y-1.5 pt-2 border-t border-slate-900">
              {investigation.findings.map((finding, idx) => (
                <li
                  key={idx}
                  className="text-xs bg-slate-900/80 p-2 rounded border border-slate-800/80 flex items-start gap-2 text-slate-300"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* SECTION 2: AI DIAGNOSIS & INFERENCE */}
        <div className="bg-purple-950/20 p-4 rounded-lg border border-purple-900/40 space-y-3">
          <div className="flex items-center justify-between border-b border-purple-800/30 pb-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
              <BrainCircuit className="w-3.5 h-3.5 text-purple-400" />
              <span>AI Diagnosis & Root-Cause Inference</span>
            </h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
              Advisory Hypothesis
            </span>
          </div>

          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              Diagnosis
            </span>
            <p className="text-sm bg-slate-950 p-3 rounded-md border border-slate-800 font-sans text-slate-200 leading-relaxed">
              {investigation.diagnosis || investigation.summary || 'No diagnosis available.'}
            </p>
          </div>

          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              Likely Explanation
            </span>
            <div className="bg-slate-950 p-3 rounded border border-slate-800 flex items-center gap-2">
              <span className={`text-sm font-semibold ${isLowConfidence ? 'text-amber-300' : 'text-purple-300'}`}>
                {investigation.likely_cause || investigation.most_likely_cause || 'UNKNOWN'}
              </span>
            </div>
          </div>

          {/* Possible Causes Breakdown */}
          {investigation.possible_causes && investigation.possible_causes.length > 0 && (
            <div className="space-y-2 pt-1">
              <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-purple-400" />
                <span>Alternative Hypotheses</span>
              </h5>
              <div className="space-y-2">
                {investigation.possible_causes.map((pc, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-950 p-2.5 rounded-md border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                  >
                    <div className="space-y-0.5">
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
        </div>

        {/* SECTION 3: EXPLICIT LIMITATIONS */}
        {investigation.limitations && investigation.limitations.length > 0 && (
          <div className="bg-amber-950/30 border border-amber-900/50 rounded-lg p-3.5 space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Audit Limitations & Uncertainty Bounds</span>
            </h4>
            <ul className="space-y-1 text-xs text-amber-200/90 font-mono">
              {investigation.limitations.map((lim, lIdx) => (
                <li key={lIdx} className="flex items-start gap-2">
                  <span className="text-amber-500">•</span>
                  <span>{lim}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* SECTION 4: ADVISORY RECOMMENDATION & HUMAN GOVERNANCE */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
          <div className="bg-slate-950/90 p-3.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-1 flex items-center gap-1">
                <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
                Advisory Action Recommendation
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className="px-2.5 py-1 rounded bg-blue-950 border border-blue-700 text-blue-300 font-mono font-bold text-sm tracking-wider">
                  {investigation.recommended_action || 'REVIEW'}
                </span>
                <span className="text-[11px] text-slate-400">
                  (Advisory only — requires human sign-off)
                </span>
              </div>
            </div>
          </div>

          <div className="bg-slate-950/90 p-3.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center gap-2 text-amber-400 font-medium text-xs">
              <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span>Authoritative Human Review Status</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              AI diagnoses do not alter reconciliation outcomes. A designated financial controller must review evidence and render the final decision.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
