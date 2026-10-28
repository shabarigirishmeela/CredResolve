import React from 'react';
import { ExplainabilityReport } from '../types';
import { PriorityBadge } from './PriorityBadge';
import {
  X, AlertTriangle, Clock, ShieldCheck,
  CheckCircle, Info, PhoneCall,
  MessageSquare, Scale
} from 'lucide-react';

interface ExplainabilityModalProps {
  accountId: string;
  report: ExplainabilityReport | null;
  isOpen: boolean;
  onClose: () => void;
  onTriggerAction?: (actionType: string) => void;
}

export const ExplainabilityModal: React.FC<ExplainabilityModalProps> = ({
  accountId,
  report,
  isOpen,
  onClose,
  onTriggerAction
}) => {
  if (!isOpen || !report) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                Prioritization Rationale & Explainability
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {accountId}
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Transparent multi-factor rule engine evaluation with compliance checks
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="max-h-[75vh] overflow-y-auto p-6 space-y-6">

          {/* Priority Score & Tier Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-slate-800/40">
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                Calculated Priority Score
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="font-mono text-3xl font-extrabold text-white">
                  {report.score.toFixed(1)}
                </span>
                <span className="text-xs text-slate-400">/ 100 max</span>
                <PriorityBadge tier={report.tier} size="md" />
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                Recommended Next Action
              </span>
              <div className="mt-1 text-sm font-semibold text-indigo-400 max-w-xs">
                {report.recommended_action}
              </div>
            </div>
          </div>

          {/* Compliance Guardrail Alert (if active) */}
          {report.compliance_hold ? (
            <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 space-y-1">
              <div className="flex items-center gap-2 font-semibold text-sm text-rose-400">
                <AlertTriangle className="w-4 h-4" />
                Mandatory Compliance Guardrail Active
              </div>
              <p className="text-xs text-rose-300/90 leading-relaxed">
                {report.compliance_reason}
              </p>
              <div className="text-[11px] text-rose-400/80 pt-1 font-mono">
                Enforcement: Fair Practices Code & Consumer Protection Act (No automated dialer or field visit allowed).
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 rounded-lg">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Compliance Clear: No open high-severity disputes or regulatory restrictions on this account.</span>
            </div>
          )}

          {/* Contact Window Check */}
          <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-800/30 text-xs">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <span className="text-slate-300">Borrower Local Time ({report.timezone}):</span>
              <span className="font-mono font-medium text-white">{report.borrower_local_time}</span>
            </div>
            <div>
              {report.contact_window_open ? (
                <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  Window Open (08:00 - 19:00)
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
                  Window Closed — Calling Restricted
                </span>
              )}
            </div>
          </div>

          {/* 5-Factor Mathematical Breakdown Table */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-indigo-400" />
              Factor Weights & Point Allocation
            </h4>
            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Factor</th>
                    <th className="py-2.5 px-3">Value</th>
                    <th className="py-2.5 px-3">Weight</th>
                    <th className="py-2.5 px-3">Points</th>
                    <th className="py-2.5 px-3">Evaluation Rationale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {report.factors.map((f, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 font-medium text-slate-200">{f.factor_name}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-300">{String(f.raw_value)}</td>
                      <td className="py-2.5 px-3 text-slate-400 font-mono">{(f.weight * 100).toFixed(0)}%</td>
                      <td className="py-2.5 px-3 font-mono font-semibold text-indigo-400">+{f.points_awarded.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-slate-400 text-[11px] leading-tight">{f.rationale}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Quick Action Simulator */}
          {onTriggerAction && (
            <div className="pt-2 border-t border-slate-800">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                Simulate Agent Next Action
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => onTriggerAction('LOG_CALL')}
                  disabled={report.compliance_hold || !report.contact_window_open}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors"
                >
                  <PhoneCall className="w-3.5 h-3.5" />
                  Initiate Call
                </button>
                <button
                  onClick={() => onTriggerAction('SEND_WHATSAPP')}
                  disabled={report.compliance_hold}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  Send WhatsApp Link
                </button>
                <button
                  onClick={() => onTriggerAction('SUBMIT_PTP')}
                  disabled={report.compliance_hold}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-purple-600 hover:bg-purple-500 text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Record PTP
                </button>
                <button
                  onClick={() => onTriggerAction('COMPLIANCE_REVIEW')}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-600/80 hover:bg-rose-500 text-white flex items-center gap-1.5 transition-colors ml-auto"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Request Compliance Review
                </button>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="border-t border-slate-800 bg-slate-900/90 px-6 py-3 flex justify-between items-center text-xs text-slate-400">
          <span>Formula: Sum(Factor Points) × Compliance Filter</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
};
