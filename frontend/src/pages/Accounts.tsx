import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { AccountItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import {
  CreditCard, Search, History,
  ChevronLeft, ChevronRight, RefreshCw, X
} from 'lucide-react';

interface AccountsProps {
  onOpenBorrower: (borrowerId: string) => void;
}

export const Accounts: React.FC<AccountsProps> = ({ onOpenBorrower }) => {
  const [items, setItems] = useState<AccountItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [status, setStatus] = useState('');
  const [loanType, setLoanType] = useState('');
  const [riskSegment, setRiskSegment] = useState('');
  const [search, setSearch] = useState('');

  // Account Detail Modal
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadAccounts = () => {
    setLoading(true);
    apiClient.getAccounts({
      status: status || undefined,
      loan_type: loanType || undefined,
      risk_segment: riskSegment || undefined,
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
    loadAccounts();
  }, [page, status, loanType, riskSegment]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadAccounts();
  };

  const handleViewDetail = async (accountId: string) => {
    setDetailModalOpen(true);
    setDetailLoading(true);
    try {
      const data = await apiClient.getAccountDetail(accountId);
      setDetailData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setDetailLoading(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-indigo-400" />
            Account Management & Delinquency Registry
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Complete loan registry across 30,000 accounts with lifecycle status history, credit risk buckets, and delinquency tracking.
          </p>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block">Total Portfolio Registry</span>
          <span className="font-mono text-lg font-bold text-white">30,000 Accounts</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">

        {/* Search */}
        <form onSubmit={handleSearch} className="flex items-center gap-2 max-w-xs w-full">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search Account ID or Borrower ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shrink-0"
          >
            Filter
          </button>
        </form>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Account Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="DELINQUENT">Delinquent</option>
            <option value="PAID">Paid</option>
            <option value="CLOSED">Closed</option>
            <option value="WRITEOFF">Writeoff</option>
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

          <select
            value={riskSegment}
            onChange={(e) => { setRiskSegment(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Risk Tiers</option>
            <option value="NPA">NPA</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>

          <button
            onClick={loadAccounts}
            title="Refresh List"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>

      </div>

      {/* Accounts Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Account ID</th>
                <th className="py-3 px-4 font-semibold">Borrower</th>
                <th className="py-3 px-4 font-semibold">Loan Product</th>
                <th className="py-3 px-4 font-semibold">Principal</th>
                <th className="py-3 px-4 font-semibold">Outstanding Balance</th>
                <th className="py-3 px-4 font-semibold">DPD & Status</th>
                <th className="py-3 px-4 font-semibold">Priority Tier</th>
                <th className="py-3 px-4 font-semibold text-right">Lifecycle History</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Loading account registry...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No matching accounts found.
                  </td>
                </tr>
              ) : (
                items.map((acc) => (
                  <tr key={acc.account_id} className="hover:bg-slate-800/40 transition-colors group">

                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-white group-hover:text-indigo-400 transition-colors">
                        {acc.account_id}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <button
                        onClick={() => acc.borrower_id && onOpenBorrower(acc.borrower_id)}
                        className="text-slate-300 hover:text-white font-medium underline truncate block text-left"
                      >
                        {acc.borrower_name}
                      </button>
                      <span className="font-mono text-[10px] text-slate-500">{acc.borrower_id}</span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="text-slate-300 font-medium">{acc.loan_type}</span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono text-slate-400">
                        ₹{acc.principal_amount.toLocaleString()}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-amber-400 text-sm">
                        ₹{acc.outstanding_amount.toLocaleString()}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className={`font-mono px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                          acc.dpd >= 90 ? 'bg-rose-500/20 text-rose-300' :
                          acc.dpd > 0 ? 'bg-amber-500/20 text-amber-300' :
                          'bg-emerald-500/20 text-emerald-300'
                        }`}>
                          {acc.dpd} DPD
                        </span>
                        <StatusBadge status={acc.status} />
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <PriorityBadge tier={acc.priority_tier} score={acc.priority_score} size="sm" />
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleViewDetail(acc.account_id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                      >
                        <History className="w-3.5 h-3.5 text-indigo-400" />
                        Timeline
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

      {/* Account Detail & Status History Modal */}
      {detailModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">

            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                  <History className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white flex items-center gap-2">
                    Account Lifecycle & Status History
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {detailData?.account_id}
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">Chronological transition log from account_status_history.csv</p>
                </div>
              </div>
              <button
                onClick={() => setDetailModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 max-h-[70vh] overflow-y-auto space-y-6">
              {detailLoading ? (
                <div className="text-center py-12 text-slate-400 text-xs">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                  Loading account timeline...
                </div>
              ) : !detailData ? (
                <div className="text-center py-12 text-slate-500 text-xs">No account records found.</div>
              ) : (
                <>
                  {/* Account Overview Bar */}
                  <div className="grid grid-cols-4 gap-3 p-3.5 rounded-xl border border-slate-800 bg-slate-800/40 text-xs">
                    <div>
                      <span className="text-slate-500 block">Product</span>
                      <span className="font-semibold text-white">{detailData.loan_type}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Outstanding</span>
                      <span className="font-mono font-bold text-amber-400">₹{detailData.outstanding_amount.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Current Status</span>
                      <StatusBadge status={detailData.status} />
                    </div>
                    <div>
                      <span className="text-slate-500 block">Priority</span>
                      <PriorityBadge tier={detailData.priority_tier} score={detailData.priority_score} size="sm" />
                    </div>
                  </div>

                  {/* Status History Timeline */}
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                      Historical Status Transitions
                    </h4>
                    {detailData.status_history?.length === 0 ? (
                      <div className="text-center py-6 text-slate-500 text-xs">No status change history logged for this account.</div>
                    ) : (
                      <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
                        {detailData.status_history.map((h: any, idx: number) => (
                          <div key={idx} className="relative flex items-start gap-4 pl-8">
                            <span className="absolute left-2 top-1.5 w-3 h-3 rounded-full border-2 border-indigo-500 bg-slate-900" />
                            <div className="flex-1 p-3 rounded-lg border border-slate-800 bg-slate-800/30 text-xs">
                              <div className="flex items-center justify-between mb-1">
                                <StatusBadge status={h.status} />
                                <span className="font-mono text-[11px] text-slate-400">{h.event_at}</span>
                              </div>
                              <div className="text-slate-400 text-[11px]">
                                Source: <strong className="text-slate-300">{h.source || 'CORE'}</strong> • Changed by: <span className="font-mono">{h.changed_by || 'SYSTEM'}</span>
                              </div>
                              {h.recorded_at && (
                                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                  Recorded at: {h.recorded_at}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-900/90 text-right">
              <button
                onClick={() => setDetailModalOpen(false)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
              >
                Close Timeline
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
