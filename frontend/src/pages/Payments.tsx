import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { PaymentItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import {
  Receipt, DollarSign, CheckCircle2, AlertTriangle,
  Search, Filter, ChevronLeft, ChevronRight, RefreshCw,
  Copy, Layers
} from 'lucide-react';

export const Payments: React.FC = () => {
  const [items, setItems] = useState<PaymentItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [status, setStatus] = useState('');
  const [method, setMethod] = useState('');
  const [isDuplicate, setIsDuplicate] = useState<string>('');
  const [search, setSearch] = useState('');

  const loadData = () => {
    setLoading(true);
    Promise.all([
      apiClient.getPayments({
        status: status || undefined,
        method: method || undefined,
        is_duplicate: isDuplicate === '' ? undefined : isDuplicate === 'true',
        search: search || undefined,
        page,
        page_size: pageSize
      }),
      apiClient.getPaymentSummary()
    ])
      .then(([pRes, sRes]) => {
        setItems(pRes.items);
        setTotal(pRes.total);
        setSummary(sRes);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [page, status, method, isDuplicate]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Receipt className="w-5 h-5 text-indigo-400" />
            Payment Management & Financial Reconciliation
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time ledger of borrower payments, idempotency tracking, payment method distribution, and duplicate reference audits.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 rounded-lg font-mono">
          <Layers className="w-4 h-4" />
          <span>Strict Idempotency Verification Active</span>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Payment Events"
          value={summary?.total_payments_recorded?.toLocaleString() || '25,000'}
          subtitle="Processed & Deduplicated"
          icon={<Receipt className="w-5 h-5 text-blue-400" />}
          variant="default"
        />

        <MetricCard
          title="Successful Collections"
          value={`₹${((summary?.total_successful_amount || 0) / 10000000).toFixed(2)} Cr`}
          subtitle={`Success Rate: ${summary?.success_rate_pct || 0}%`}
          change="Clean Realized"
          isPositive={true}
          icon={<CheckCircle2 className="w-5 h-5 text-emerald-400" />}
          variant="success"
        />

        <MetricCard
          title="Duplicate Txn References"
          value={summary?.duplicate_reference_count?.toLocaleString() || '0'}
          subtitle="Cross-Account/Retry Duplicates"
          change="Audit Flagged"
          isPositive={false}
          icon={<Copy className="w-5 h-5 text-amber-400" />}
          variant="warning"
        />

        <MetricCard
          title="Failed / Reversed Volume"
          value={`₹${(((summary?.by_status?.FAILED?.amount || 0) + (summary?.by_status?.REVERSED?.amount || 0)) / 10000000).toFixed(2)} Cr`}
          subtitle="Requires Retries & Follow-up"
          change="Action Needed"
          isPositive={false}
          icon={<AlertTriangle className="w-5 h-5 text-rose-400" />}
          variant="danger"
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">

        {/* Search */}
        <form onSubmit={handleSearch} className="flex items-center gap-2 max-w-xs w-full">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search Reference, Payment ID, Account ID..."
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
            <option value="">All Payment Statuses</option>
            <option value="SUCCESS">Success</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
            <option value="REVERSED">Reversed</option>
          </select>

          <select
            value={method}
            onChange={(e) => { setMethod(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Payment Methods</option>
            <option value="UPI">UPI</option>
            <option value="CARD">Card</option>
            <option value="NETBANKING">Netbanking</option>
            <option value="CASH">Cash (Field)</option>
            <option value="ACH">NACH / AutoDebit</option>
          </select>

          <select
            value={isDuplicate}
            onChange={(e) => { setIsDuplicate(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Reference Types</option>
            <option value="false">Unique References Only</option>
            <option value="true">Duplicate References Only</option>
          </select>

          <button
            onClick={loadData}
            title="Refresh Payments"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>

      </div>

      {/* Payments Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Payment ID</th>
                <th className="py-3 px-4 font-semibold">Account & Borrower</th>
                <th className="py-3 px-4 font-semibold">Amount</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Method</th>
                <th className="py-3 px-4 font-semibold">Txn Reference</th>
                <th className="py-3 px-4 font-semibold">Event Timestamp</th>
                <th className="py-3 px-4 font-semibold text-right">Integrity Audit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Fetching payment transactions...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No payment records match current filters.
                  </td>
                </tr>
              ) : (
                items.map((p) => (
                  <tr key={p.payment_id} className="hover:bg-slate-800/40 transition-colors">

                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-white">{p.payment_id}</span>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono text-slate-300">{p.account_id}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{p.borrower_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-white text-sm">
                        ₹{p.amount.toLocaleString()}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <StatusBadge status={p.payment_status} />
                    </td>

                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]">
                        {p.payment_method}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono text-slate-300 text-[11px]">
                        {p.payment_reference || 'N/A'}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono text-slate-400 text-[11px]">{p.event_at}</span>
                    </td>

                    <td className="py-3 px-4 text-right">
                      {p.is_duplicate_ref ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded">
                          <Copy className="w-3 h-3" /> Duplicate Ref
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                          <CheckCircle2 className="w-3 h-3" /> Unique
                        </span>
                      )}
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
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} payments
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

    </div>
  );
};
