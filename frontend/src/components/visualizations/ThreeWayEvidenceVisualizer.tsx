import React from 'react';
import {
  CreditCard,
  Building2,
  BookOpen,
  AlertTriangle,
  Split,
} from 'lucide-react';
import { SourceRecord } from '../../api/types';

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

  // Derive variance either from explicit prop or actual amounts
  const hasAmountVariance =
    difference !== null && difference !== undefined && Math.abs(difference) > 0;

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-5 shadow-lg">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-blue-600/20 text-blue-400 border border-blue-500/30">
            <Split className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-white">
              3-Way Financial Parity Comparison
            </h4>
            <span className="text-[11px] font-mono text-slate-400">
              Txn Reference: <strong className="text-blue-400">{transactionId}</strong>
            </span>
          </div>
        </div>

        {hasAmountVariance && (
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-rose-950/80 border border-rose-800 text-rose-300 font-mono text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
            <span>Net Variance: ₹{Math.abs(difference!).toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Visual Tree / Node Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
        {/* 1. Payment Gateway Leg */}
        <div
          className={`rounded-lg p-4 border flex flex-col justify-between transition ${
            payment
              ? 'bg-slate-900 border-blue-900/60 shadow-blue-950/20'
              : 'bg-slate-900/50 border-rose-900/40 opacity-75'
          }`}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5" />
                <span>Payment Gateway</span>
              </span>
              {payment ? (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                  {payment.status || 'INGESTED'}
                </span>
              ) : (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  NOT AVAILABLE
                </span>
              )}
            </div>

            {payment ? (
              <div className="space-y-2 font-mono text-xs">
                <div>
                  <span className="text-[10px] text-slate-500 font-sans block">Settlement Amount</span>
                  <div className="text-base font-bold text-white">
                    {payment.currency || 'INR'} {pAmount?.toFixed(2)}
                  </div>
                  {normalizedValues?.payment && (
                    <span className="text-[10px] text-blue-400">
                      Norm: ₹{parseFloat(normalizedValues.payment).toFixed(2)}
                    </span>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] text-slate-500 font-sans block">Date</span>
                    <span className="text-slate-300">{payment.transaction_date || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 font-sans block">Customer / Ref</span>
                    <span className="text-slate-300 truncate block" title={payment.customer_id || payment.reference_id || ''}>
                      {payment.customer_id || payment.reference_id || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-rose-400/80 font-mono italic">
                Missing from Payment Gateway Stream
              </div>
            )}
          </div>
        </div>

        {/* 2. Bank Settlement Leg */}
        <div
          className={`rounded-lg p-4 border flex flex-col justify-between transition ${
            bank
              ? hasAmountVariance && bAmount !== pAmount
                ? 'bg-slate-900 border-rose-800/80 shadow-rose-950/20'
                : 'bg-slate-900 border-emerald-900/60 shadow-emerald-950/20'
              : 'bg-slate-900/50 border-rose-900/40 opacity-75'
          }`}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5" />
                <span>Bank Settlement</span>
              </span>
              {bank ? (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  hasAmountVariance && bAmount !== pAmount
                    ? 'bg-rose-950 text-rose-300 border-rose-800'
                    : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                }`}>
                  {bank.status || 'SETTLED'}
                </span>
              ) : (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  NOT AVAILABLE
                </span>
              )}
            </div>

            {bank ? (
              <div className="space-y-2 font-mono text-xs">
                <div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] text-slate-500 font-sans block">Settlement Amount</span>
                    {hasAmountVariance && bAmount !== pAmount && (
                      <span className="text-[10px] font-bold text-rose-400">DISCREPANCY</span>
                    )}
                  </div>
                  <div className={`text-base font-bold ${
                    hasAmountVariance && bAmount !== pAmount ? 'text-rose-400' : 'text-white'
                  }`}>
                    {bank.currency || 'INR'} {bAmount?.toFixed(2)}
                  </div>
                  {normalizedValues?.bank && (
                    <span className="text-[10px] text-emerald-400">
                      Norm: ₹{parseFloat(normalizedValues.bank).toFixed(2)}
                    </span>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] text-slate-500 font-sans block">Date</span>
                    <span className="text-slate-300">{bank.transaction_date || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 font-sans block">Bank / Account</span>
                    <span className="text-slate-300 truncate block" title={bank.reference_id || ''}>
                      {bank.reference_id || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-rose-400/80 font-mono italic">
                Missing from Bank Statement Stream
              </div>
            )}
          </div>
        </div>

        {/* 3. Internal Ledger Leg */}
        <div
          className={`rounded-lg p-4 border flex flex-col justify-between transition ${
            ledger
              ? hasAmountVariance && lAmount !== pAmount
                ? 'bg-slate-900 border-rose-800/80 shadow-rose-950/20'
                : 'bg-slate-900 border-purple-900/60 shadow-purple-950/20'
              : 'bg-slate-900/50 border-rose-900/40 opacity-75'
          }`}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5" />
                <span>Internal Ledger</span>
              </span>
              {ledger ? (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  hasAmountVariance && lAmount !== pAmount
                    ? 'bg-rose-950 text-rose-300 border-rose-800'
                    : 'bg-purple-950 text-purple-300 border-purple-800'
                }`}>
                  {ledger.status || 'POSTED'}
                </span>
              ) : (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  NOT AVAILABLE
                </span>
              )}
            </div>

            {ledger ? (
              <div className="space-y-2 font-mono text-xs">
                <div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] text-slate-500 font-sans block">Ledger Amount</span>
                    {hasAmountVariance && lAmount !== pAmount && (
                      <span className="text-[10px] font-bold text-rose-400">DISCREPANCY</span>
                    )}
                  </div>
                  <div className={`text-base font-bold ${
                    hasAmountVariance && lAmount !== pAmount ? 'text-rose-400' : 'text-white'
                  }`}>
                    {ledger.currency || 'INR'} {lAmount?.toFixed(2)}
                  </div>
                  {normalizedValues?.ledger && (
                    <span className="text-[10px] text-purple-400">
                      Norm: ₹{parseFloat(normalizedValues.ledger).toFixed(2)}
                    </span>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[10px] text-slate-500 font-sans block">Date</span>
                    <span className="text-slate-300">{ledger.transaction_date || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 font-sans block">Account Code</span>
                    <span className="text-slate-300 truncate block" title={ledger.reference_id || ''}>
                      {ledger.reference_id || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-rose-400/80 font-mono italic">
                Missing from General Ledger Stream
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Visual Connection Footer */}
      <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-[11px]">Rule Classification:</span>
          <span className="font-mono font-semibold text-rose-300">
            {exceptionType || 'None'}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${payment ? 'bg-blue-400' : 'bg-rose-500'}`} />
            Payment {payment ? '✓' : '✗'}
          </span>
          <span className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${bank ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            Bank {bank ? '✓' : '✗'}
          </span>
          <span className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${ledger ? 'bg-purple-400' : 'bg-rose-500'}`} />
            Ledger {ledger ? '✓' : '✗'}
          </span>
        </div>
      </div>
    </div>
  );
};
