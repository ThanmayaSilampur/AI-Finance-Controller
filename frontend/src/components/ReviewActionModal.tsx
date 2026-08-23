import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  XCircle,
  ArrowUpRight,
  AlertCircle,
  Loader2,
  Info,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import { ExceptionItem, ReviewResponse } from '../api/types';

interface ReviewActionModalProps {
  exception: ExceptionItem;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updated: ReviewResponse) => void;
}

export const ReviewActionModal: React.FC<ReviewActionModalProps> = ({
  exception,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED' | 'ESCALATED'>('APPROVED');
  const [reviewer, setReviewer] = useState<string>('finance_controller');
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const isAlreadyResolved = exception.review_status !== 'PENDING';
  const allowedDecisions: Array<'APPROVED' | 'REJECTED' | 'ESCALATED'> = isAlreadyResolved
    ? ['ESCALATED']
    : ['APPROVED', 'REJECTED', 'ESCALATED'];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!reviewer.trim()) {
      setErrorMessage('Reviewer identification is mandatory for audit compliance.');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await api.reviewException(exception.exception_id, {
        decision,
        reviewer: reviewer.trim(),
        comment: comment.trim(),
      });
      setIsSubmitting(false);
      onSuccess(res);
      onClose();
    } catch (err: any) {
      setIsSubmitting(false);
      if (err instanceof ApiError) {
        setErrorMessage(err.message || `Review transition failed (${err.code || err.status})`);
      } else {
        setErrorMessage(err.message || 'An unexpected error occurred while submitting review.');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
          <div>
            <h3 className="text-base font-semibold text-white">Exception Human Review</h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Exception ID: {exception.exception_id} • Transaction: {exception.transaction_id}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Current State Summary */}
        <div className="px-6 py-3 bg-slate-850/60 border-b border-slate-800/80 flex items-center justify-between text-xs">
          <div>
            <span className="text-slate-400">Current Status: </span>
            <span className="font-mono font-semibold text-amber-400">{exception.review_status}</span>
          </div>
          <div>
            <span className="text-slate-400">Exception Type: </span>
            <span className="font-mono text-slate-200">{exception.exception_type}</span>
          </div>
          {exception.difference !== null && (
            <div>
              <span className="text-slate-400">Difference: </span>
              <span className="font-mono font-semibold text-rose-400">₹{exception.difference.toFixed(2)}</span>
            </div>
          )}
        </div>

        {isAlreadyResolved && (
          <div className="mx-6 mt-4 p-3 rounded bg-purple-950/60 border border-purple-800/60 flex items-start gap-2.5 text-xs text-purple-200">
            <Info className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
            <div>
              This exception has already been reviewed ({exception.review_status}). Under governance rules,
              already-resolved exceptions can only be <strong>ESCALATED</strong> for higher-level controller review.
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMessage && (
            <div className="p-3 rounded bg-rose-950/80 border border-rose-800 flex items-start gap-2.5 text-xs text-rose-200">
              <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Decision Selection */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Review Decision
            </label>
            <div className="grid grid-cols-3 gap-2">
              {allowedDecisions.includes('APPROVED') && (
                <button
                  type="button"
                  onClick={() => setDecision('APPROVED')}
                  className={`p-3 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition ${
                    decision === 'APPROVED'
                      ? 'bg-emerald-950 border-emerald-500 text-emerald-300 ring-1 ring-emerald-500'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>APPROVE</span>
                </button>
              )}

              {allowedDecisions.includes('REJECTED') && (
                <button
                  type="button"
                  onClick={() => setDecision('REJECTED')}
                  className={`p-3 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition ${
                    decision === 'REJECTED'
                      ? 'bg-red-950 border-red-500 text-red-300 ring-1 ring-red-500'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <XCircle className="w-4 h-4 text-red-400" />
                  <span>REJECT</span>
                </button>
              )}

              {allowedDecisions.includes('ESCALATED') && (
                <button
                  type="button"
                  onClick={() => setDecision('ESCALATED')}
                  className={`p-3 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition ${
                    decision === 'ESCALATED'
                      ? 'bg-purple-950 border-purple-500 text-purple-300 ring-1 ring-purple-500'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <ArrowUpRight className="w-4 h-4 text-purple-400" />
                  <span>ESCALATE</span>
                </button>
              )}
            </div>
          </div>

          {/* Reviewer Field */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Reviewer Identifier <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="e.g. finance_controller or risk_analyst"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>

          {/* Comment Field */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Audit Rationale / Comment
            </label>
            <textarea
              rows={3}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="State justification (e.g. Confirmed MDR processing fee schedule match)."
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 resize-none font-sans"
            />
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-750 rounded-md transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-md transition flex items-center gap-1.5 shadow-lg shadow-blue-900/30 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Recording Audit...
                </>
              ) : (
                'Commit Review Decision'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
