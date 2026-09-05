import React from 'react';
import {
  FileSearch,
  Scale,
  BrainCircuit,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';

interface InvestigationPipelineProps {
  currentStage: 'facts' | 'deterministic' | 'ai' | 'review' | 'completed';
  exceptionType?: string | null;
  variance?: number | null;
  aiStatus?: string | null;
  reviewStatus?: string | null;
}

export const InvestigationPipeline: React.FC<InvestigationPipelineProps> = ({
  currentStage,
  exceptionType,
  variance,
  aiStatus,
  reviewStatus,
}) => {
  const steps = [
    {
      id: 'facts',
      title: 'Source Facts',
      subtitle: '3-Way Ingested Records',
      icon: FileSearch,
      color: 'blue',
      badge: 'Deterministic',
    },
    {
      id: 'deterministic',
      title: 'Deterministic Result',
      subtitle: exceptionType ? exceptionType.replace(/_/g, ' ') : 'Parity Evaluated',
      icon: Scale,
      color: 'rose',
      badge: variance !== null && variance !== undefined ? `₹${Math.abs(variance).toFixed(2)}` : 'Rule-Based',
    },
    {
      id: 'ai',
      title: 'AI Investigation',
      subtitle: aiStatus || 'Advisory Hypothesis',
      icon: BrainCircuit,
      color: 'purple',
      badge: 'Evidence-First',
    },
    {
      id: 'review',
      title: 'Human Review',
      subtitle: reviewStatus || 'Pending Decision',
      icon: ShieldCheck,
      color: 'emerald',
      badge: reviewStatus === 'APPROVED' ? 'Approved' : 'Governance',
    },
  ];

  return (
    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 shadow-md">
      <div className="flex items-center justify-between border-b border-slate-850 pb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Decision Lineage Pipeline
        </span>
        <span className="text-[10px] font-mono text-slate-500">
          Immutable Audit Verification
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {steps.map((step) => {
          const Icon = step.icon;
          const isCurrent = step.id === currentStage;
          const isCompleted =
            step.id === 'facts' ||
            step.id === 'deterministic' ||
            (step.id === 'ai' && currentStage !== 'facts' && currentStage !== 'deterministic') ||
            reviewStatus === 'APPROVED' ||
            reviewStatus === 'REJECTED';

          return (
            <div
              key={step.id}
              className={`p-3 rounded-lg border relative flex flex-col justify-between transition ${
                isCurrent
                  ? 'bg-slate-900 border-blue-600/80 shadow-md shadow-blue-950/40'
                  : 'bg-slate-900/40 border-slate-800'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`p-1.5 rounded-md ${
                      step.color === 'blue'
                        ? 'bg-blue-950 text-blue-400 border border-blue-800'
                        : step.color === 'rose'
                        ? 'bg-rose-950 text-rose-400 border border-rose-800'
                        : step.color === 'purple'
                        ? 'bg-purple-950 text-purple-400 border border-purple-800'
                        : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-semibold text-white tracking-wide">
                    {step.title}
                  </span>
                </div>
                {isCompleted && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                )}
              </div>

              <div className="flex items-baseline justify-between mt-1 text-[11px] font-mono">
                <span className="text-slate-400 truncate max-w-[120px]" title={step.subtitle}>
                  {step.subtitle}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800 font-medium">
                  {step.badge}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
