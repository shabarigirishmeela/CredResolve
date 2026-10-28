import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { AccountItem, ExplainabilityReport } from '../types';
import { PriorityBadge } from '../components/PriorityBadge';
import { StatusBadge } from '../components/StatusBadge';
import { ExplainabilityModal } from '../components/ExplainabilityModal';
import {
  Sparkles, Search, Filter, AlertTriangle,
  HelpCircle, ChevronLeft, ChevronRight, RefreshCw,
  PhoneCall, ShieldAlert, CheckCircle2
} from 'lucide-react';

interface WorkQueueProps {
  onOpenBorrower: (borrowerId: string) => void;
}

export const WorkQueue: React.FC<WorkQueueProps> = ({ onOpenBorrower }) => {
  const [items, setItems] = useState<AccountItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [tier, setTier] = useState('');
  const [complianceHold, setComplianceHold] = useState<string>('');
  const [loanType, setLoanType] = useState('');
  const [search, setSearch] = useState('');

  // Explainability modal state
  const [selectedAccId, setSelectedAccId] = useState<string | null>(null);
  const [report, setReport] = useState<ExplainabilityReport | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const loadQueue = () => {
    setLoading(true);
    apiClient.getWorkQueue({
      tier: tier || undefined,
      compliance_hold: complianceHold === '' ? undefined : complianceHold === 'true',
      loan_type: loanType || undefined,
      search: search || undefined,
      page,
      page_size: pageSize
    })
      .then(res => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadQueue();
  }, [page, tier, complianceHold, loanType]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadQueue();
  };

  const handleOpenExplain = async (accountId: string) => {
    setSelectedAccId(accountId);
    try {
      const rep = await apiClient.explainPriority(accountId);
      setReport(rep);
      setModalOpen(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTriggerAction = async (actionType: string) => {
    if (!selectedAccId) return;
    try {
      const res = await apiClient.logQueueAction(selectedAccId, { action_type: actionType });
      setActionSuccessMsg(res.message);
      loadQueue();
      // Re-fetch report
      const updatedRep = await apiClient.explainPriority(selectedAccId);
      setReport(updatedRep);
      setTimeout(() => setActionSuccessMsg(null), 4000);
    } catch (err) {
      console.error(err);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-indigo-950/60 via-slate-900 to-slate-900 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            Transparent Rule-Based Recommendation Engine
          </div>
          <h2 className="text-xl font-extrabold text-white tracking-tight">
            Prioritized Collection Work Queue
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Accounts dynamically scored (0–100) using DPD urgency, exposure value, risk tier, PTP history, and contact responsiveness with strict RBI Fair Practices compliance pauses.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-xs text-slate-400 block">Queue Capacity</span>
            <span className="font-mono text-lg font-bold text-white">
              {total.toLocaleString()} Accounts
            </span>
          </div>
        </div>
      </div>

      {actionSuccessMsg && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 max-w-xs w-full">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search Account or Borrower ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
          >
            Filter
          </button>
        </form>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={tier}
            onChange={(e) => { setTier(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Priority Tiers</option>
            <option value="CRITICAL">Critical (Score 75-100)</option>
            <option value="HIGH">High (Score 55-74)</option>
            <option value="MEDIUM">Medium (Score 35-54)</option>
            <option value="LOW">Low (Score 0-34)</option>
          </select>

          <select
            value={complianceHold}
            onChange={(e) => { setComplianceHold(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Compliance States</option>
            <option value="false">Clear to Contact</option>
            <option value="true">Compliance Pause Active</option>
          </select>

          <select
            value={loanType}
            onChange={(e) => { setLoanType(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Loan Products</option>
            <option value="CONSUMER">Consumer</option>
            <option value="BNPL">BNPL</option>
            <option value="CREDIT_CARD">Credit Card</option>
            <option value="PERSONAL">Personal</option>
            <option value="AUTO">Auto</option>
          </select>

          <button
            onClick={loadQueue}
            title="Refresh Queue"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>

      </div>

      {/* Prioritized Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3.5 px-4 font-semibold">Priority & Score</th>
                <th className="py-3.5 px-4 font-semibold">Account & Borrower</th>
                <th className="py-3.5 px-4 font-semibold">Product</th>
                <th className="py-3.5 px-4 font-semibold">Exposure Balance</th>
                <th className="py-3.5 px-4 font-semibold">DPD & Risk</th>
                <th className="py-3.5 px-4 font-semibold">Recommended Action</th>
                <th className="py-3.5 px-4 font-semibold text-right">Explainability & Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Evaluating collection priorities...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No matching accounts in prioritized queue.
                  </td>
                </tr>
              ) : (
                items.map((acc) => (
                  <tr key={acc.account_id} className="hover:bg-slate-800/40 transition-colors group">

                    {/* Score & Tier */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <PriorityBadge tier={acc.priority_tier} score={acc.priority_score} size="md" />
                      </div>
                    </td>

                    {/* Account & Borrower */}
                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-white group-hover:text-indigo-400 transition-colors">
                        {acc.account_id}
                      </div>
                      <button
                        onClick={() => acc.borrower_id && onOpenBorrower(acc.borrower_id)}
                        className="text-slate-400 hover:text-slate-200 text-[11px] underline truncate block text-left"
                      >
                        {acc.borrower_name} ({acc.borrower_id})
                      </button>
                    </td>

                    {/* Loan Product */}
                    <td className="py-3 px-4">
                      <span className="font-medium text-slate-300">{acc.loan_type}</span>
                    </td>

                    {/* Exposure */}
                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-amber-400 text-sm">
                        ₹{acc.outstanding_amount.toLocaleString()}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        Principal: ₹{acc.principal_amount.toLocaleString()}
                      </div>
                    </td>

                    {/* DPD & Risk */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className={`font-mono font-semibold px-1.5 py-0.5 rounded text-[11px] ${
                          acc.dpd >= 90 ? 'bg-rose-500/20 text-rose-300' :
                          acc.dpd >= 60 ? 'bg-amber-500/20 text-amber-300' :
                          'bg-blue-500/20 text-blue-300'
                        }`}>
                          {acc.dpd} DPD
                        </span>
                        <StatusBadge status={acc.risk_segment} />
                      </div>
                    </td>

                    {/* Recommended Action & Compliance */}
                    <td className="py-3 px-4 max-w-xs">
                      {acc.compliance_hold ? (
                        <div className="flex items-center gap-1.5 text-rose-400 text-[11px] font-semibold bg-rose-500/10 border border-rose-500/25 px-2 py-1 rounded-lg">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          <span className="truncate">{acc.recommended_action}</span>
                        </div>
                      ) : (
                        <div className="text-slate-200 font-medium truncate">
                          {acc.recommended_action}
                        </div>
                      )}
                    </td>

                    {/* Actions & Explainability Button */}
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleOpenExplain(acc.account_id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 transition-all shadow-sm"
                      >
                        <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                        Explain Score
                      </button>
                    </td>

                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} accounts
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-slate-300">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>

      {/* Explainability Modal */}
      <ExplainabilityModal
        accountId={selectedAccId || ''}
        report={report}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onTriggerAction={handleTriggerAction}
      />

    </div>
  );
};
