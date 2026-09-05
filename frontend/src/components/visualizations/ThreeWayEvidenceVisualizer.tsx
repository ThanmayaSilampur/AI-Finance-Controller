import React from 'react';
import {
  CreditCard,
  Building2,
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  Scale,
} from 'lucide-react';
import { SourceRecord } from '../../api/types';
import { formatCurrency, formatDate } from '../../utils/formatters';

interface ThreeWayEvidenceVisualizerProps {
  transactionId: string;
  sourceRecords?: {
    payment?: SourceRecord;
    bank?: SourceRecord;
    ledger?: SourceRecord;
  };
  normalizedValues?: {
    payment: string | null;
    bank: string | null;
    ledger: string | null;
  };
  exceptionType?: string | null;
  difference?: number | null;
}

export const ThreeWayEvidenceVisualizer: React.FC<ThreeWayEvidenceVisualizerProps> = ({
  transactionId,
  sourceRecords,
  normalizedValues,
  exceptionType,
  difference,
}) => {
  const payment = sourceRecords?.payment;
  const bank = sourceRecords?.bank;
  const ledger = sourceRecords?.ledger;

  const pAmount = payment ? parseFloat(payment.amount || '0') : null;
  const bAmount = bank ? parseFloat(bank.amount || '0') : null;
  const lAmount = ledger ? parseFloat(ledger.amount || '0') : null;

  const hasAmountVariance =
    difference !== null && difference !== undefined && Math.abs(difference) > 0;

  const isThreeWayBalanced =
    payment && bank && ledger && !hasAmountVariance && !exceptionType;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5 shadow-sm">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                3-Way Parity Verification
              </h4>
              {isThreeWayBalanced ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-3 h-3" />
                  Triple-Leg Parity Verified
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-full">
                  <AlertTriangle className="w-3 h-3" />
                  Parity Discrepancy
                </span>
              )}
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              Reference: <strong className="text-slate-200 font-semibold">{transactionId}</strong>
            </span>
          </div>
        </div>

        {hasAmountVariance && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 font-mono text-xs font-semibold shadow-sm">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Net Discrepancy: {formatCurrency(Math.abs(difference!))}</span>
          </div>
        )}
      </div>

      {/* 3-Leg Interactive Stream: Payment Gateway → Bank Settlement → Internal Ledger */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
        {/* 1. Payment Gateway Leg */}
        <div
          className={`rounded-xl p-4 border transition-all ${
            payment
              ? 'bg-slate-950 border-slate-800'
              : 'bg-slate-950/60 border-rose-500/30 opacity-75'
          }`}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5" />
                <span>Payment Gateway Leg</span>
              </span>
              {payment ? (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  {payment.status || 'INGESTED'}
                </span>
              ) : (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  MISSING LEG
                </span>
              )}
            </div>

            {payment ? (
              <div className="space-y-2.5 text-xs font-mono">
                <div>
                  <span className="text-[10px] font-sans text-slate-400 uppercase tracking-wider block">Gateway Settlement</span>
                  <div className="text-lg font-bold text-slate-100 tabular-nums">
                    {formatCurrency(pAmount, payment.currency || 'INR')}
                  </div>
                  {normalizedValues?.payment && (
                    <span className="text-[11px] text-blue-400 block -mt-0.5">
                      Normalized: {formatCurrency(normalizedValues.payment)}
                    </span>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] font-sans text-slate-400 block">Captured Date</span>
                    <span className="text-slate-300">{formatDate(payment.transaction_date)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-sans text-slate-400 block">Customer ID</span>
                    <span className="text-slate-300 truncate block" title={payment.customer_id || ''}>
                      {payment.customer_id || '—'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-rose-400 font-mono italic">
                Record absent from Payment Gateway stream
              </div>
            )}
          </div>
        </div>

        {/* 2. Bank Settlement Leg */}
        <div
          className={`rounded-xl p-4 border transition-all ${
            bank
              ? hasAmountVariance && bAmount !== pAmount
                ? 'bg-slate-950 border-rose-500/40 ring-1 ring-rose-500/20'
                : 'bg-slate-950 border-slate-800'
              : 'bg-slate-950/60 border-rose-500/30 opacity-75'
          }`}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5" />
                <span>Bank Statement Leg</span>
              </span>
              {bank ? (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                  hasAmountVariance && bAmount !== pAmount
                    ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                }`}>
                  {bank.status || 'SETTLED'}
                </span>
              ) : (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  MISSING LEG
                </span>
              )}
            </div>

            {bank ? (
              <div className="space-y-2.5 text-xs font-mono">
                <div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-sans text-slate-400 uppercase tracking-wider block">Posted Bank Amount</span>
                    {hasAmountVariance && bAmount !== pAmount && (
                      <span className="text-[10px] font-bold text-rose-400">AMOUNT DELTA</span>
                    )}
                  </div>
                  <div className={`text-lg font-bold tabular-nums ${
                    hasAmountVariance && bAmount !== pAmount ? 'text-rose-400' : 'text-slate-100'
                  }`}>
                    {formatCurrency(bAmount, bank.currency || 'INR')}
                  </div>
                  {normalizedValues?.bank && (
                    <span className="text-[11px] text-emerald-400 block -mt-0.5">
                      Normalized: {formatCurrency(normalizedValues.bank)}
                    </span>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] font-sans text-slate-400 block">Settled Date</span>
                    <span className="text-slate-300">{formatDate(bank.transaction_date)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-sans text-slate-400 block">Account Ref</span>
                    <span className="text-slate-300 truncate block" title={bank.reference_id || ''}>
                      {bank.reference_id || '—'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-rose-400 font-mono italic">
                Record absent from Bank Statement stream
              </div>
            )}
          </div>
        </div>

        {/* 3. Internal Ledger Leg */}
        <div
          className={`rounded-xl p-4 border transition-all ${
            ledger
              ? hasAmountVariance && lAmount !== pAmount
                ? 'bg-slate-950 border-rose-500/40 ring-1 ring-rose-500/20'
                : 'bg-slate-950 border-slate-800'
              : 'bg-slate-950/60 border-rose-500/30 opacity-75'
          }`}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5" />
                <span>General Ledger Leg</span>
              </span>
              {ledger ? (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                  hasAmountVariance && lAmount !== pAmount
                    ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                }`}>
                  {ledger.status || 'POSTED'}
                </span>
              ) : (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  MISSING LEG
                </span>
              )}
            </div>

            {ledger ? (
              <div className="space-y-2.5 text-xs font-mono">
                <div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-sans text-slate-400 uppercase tracking-wider block">GL Booking Amount</span>
                    {hasAmountVariance && lAmount !== pAmount && (
                      <span className="text-[10px] font-bold text-rose-400">AMOUNT DELTA</span>
                    )}
                  </div>
                  <div className={`text-lg font-bold tabular-nums ${
                    hasAmountVariance && lAmount !== pAmount ? 'text-rose-400' : 'text-slate-100'
                  }`}>
                    {formatCurrency(lAmount, ledger.currency || 'INR')}
                  </div>
                  {normalizedValues?.ledger && (
                    <span className="text-[11px] text-purple-400 block -mt-0.5">
                      Normalized: {formatCurrency(normalizedValues.ledger)}
                    </span>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] font-sans text-slate-400 block">Booking Date</span>
                    <span className="text-slate-300">{formatDate(ledger.transaction_date)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-sans text-slate-400 block">GL Account Code</span>
                    <span className="text-slate-300 truncate block" title={ledger.reference_id || ''}>
                      {ledger.reference_id || '—'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-rose-400 font-mono italic">
                Record absent from General Ledger stream
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Verification Summary Footer */}
      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-[11px]">Reconciliation Classification:</span>
          <span className="font-mono font-semibold text-slate-200">
            {exceptionType ? (
              <span className="text-rose-400">{exceptionType}</span>
            ) : (
              <span className="text-emerald-400">Triple-Leg Match Confirmed</span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${payment ? 'bg-blue-400' : 'bg-rose-500'}`} />
            Gateway {payment ? 'Captured' : 'Missing'}
          </span>
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${bank ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            Bank {bank ? 'Settled' : 'Missing'}
          </span>
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${ledger ? 'bg-purple-400' : 'bg-rose-500'}`} />
            GL {ledger ? 'Booked' : 'Missing'}
          </span>
        </div>
      </div>
    </div>
  );
};
