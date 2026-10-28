import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { PTPItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import {
  CalendarCheck2, DollarSign, CheckCircle, AlertOctagon,
  Search, Filter, ChevronLeft, ChevronRight, RefreshCw,
  MessageSquare, Phone, MapPin
} from 'lucide-react';

export const PromisesToPay: React.FC = () => {
  const [items, setItems] = useState<PTPItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [status, setStatus] = useState('');
  const [source, setSource] = useState('');
  const [search, setSearch] = useState('');

  const loadData = () => {
    setLoading(true);
    Promise.all([
      apiClient.getPTPs({
        status: status || undefined,
        source: source || undefined,
        search: search || undefined,
        page,
        page_size: pageSize
      }),
      apiClient.getPTPSummary()
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
  }, [page, status, source]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  const getSourceIcon = (src: string) => {
    switch (src.toUpperCase()) {
      case 'CALL': return <Phone className="w-3.5 h-3.5 text-blue-400" />;
      case 'WHATSAPP': return <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />;
      case 'SMS': return <MessageSquare className="w-3.5 h-3.5 text-amber-400" />;
      case 'FIELD': return <MapPin className="w-3.5 h-3.5 text-purple-400" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <CalendarCheck2 className="w-5 h-5 text-indigo-400" />
            Promise-to-Pay (PTP) Management
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Tracking borrower payment commitments, conversion funnel, broken PTP escalation, and channel attribution.
          </p>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block">Total PTP Commitments</span>
          <span className="font-mono text-lg font-bold text-white">
            {summary?.total_promises?.toLocaleString() || '18,000'}
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Promised Volume"
          value={`₹${((summary?.total_promised_amount || 0) / 10000000).toFixed(2)} Cr`}
          subtitle="Commitments Secured"
          icon={<DollarSign className="w-5 h-5 text-blue-400" />}
          variant="default"
        />

        <MetricCard
          title="Fulfillment Rate"
          value={`${summary?.fulfillment_rate_pct || 0}%`}
          subtitle="Kept Promises / Resolved"
          change="Conversion Benchmark"
          isPositive={true}
          icon={<CheckCircle className="w-5 h-5 text-emerald-400" />}
          variant="success"
        />

        <MetricCard
          title="Kept Promises"
          value={summary?.by_status?.KEPT?.count?.toLocaleString() || '0'}
          subtitle={`₹${((summary?.by_status?.KEPT?.amount || 0) / 10000000).toFixed(2)} Cr Recovered`}
          change="Honored Commitments"
          isPositive={true}
          icon={<CheckCircle className="w-5 h-5 text-emerald-400" />}
          variant="purple"
        />

        <MetricCard
          title="Broken Promises"
          value={summary?.by_status?.BROKEN?.count?.toLocaleString() || '0'}
          subtitle={`₹${((summary?.by_status?.BROKEN?.amount || 0) / 10000000).toFixed(2)} Cr Defaulted`}
          change="Urgent Queue Trigger"
          isPositive={false}
          icon={<AlertOctagon className="w-5 h-5 text-rose-400" />}
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
              placeholder="Search PTP ID, Account, Agent..."
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
            <option value="">All PTP Statuses</option>
            <option value="KEPT">Kept (Honored)</option>
            <option value="BROKEN">Broken (Defaulted)</option>
            <option value="OPEN">Open (Pending Date)</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          <select
            value={source}
            onChange={(e) => { setSource(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Channel Sources</option>
            <option value="CALL">Voice Call</option>
            <option value="WHATSAPP">WhatsApp</option>
            <option value="SMS">SMS Notice</option>
            <option value="FIELD">Field Visit</option>
          </select>

          <button
            onClick={loadData}
            title="Refresh PTP List"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>

      </div>

      {/* PTP Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">PTP ID</th>
                <th className="py-3 px-4 font-semibold">Account & Borrower</th>
                <th className="py-3 px-4 font-semibold">Promised Amount</th>
                <th className="py-3 px-4 font-semibold">Promised Payment Date</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Channel Source</th>
                <th className="py-3 px-4 font-semibold">Assigned Agent</th>
                <th className="py-3 px-4 font-semibold text-right">Commitment Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Fetching promise to pay records...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No PTP commitments match current filters.
                  </td>
                </tr>
              ) : (
                items.map((pt) => (
                  <tr key={pt.ptp_id} className="hover:bg-slate-800/40 transition-colors">

                    <td className="py-3 px-4 font-mono font-bold text-white">
                      {pt.ptp_id}
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono text-slate-300">{pt.account_id}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{pt.borrower_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-emerald-400 text-sm">
                        ₹{pt.promised_amount.toLocaleString()}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-300 font-medium">
                      {pt.promised_date}
                    </td>

                    <td className="py-3 px-4">
                      <StatusBadge status={pt.status} />
                    </td>

                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-medium text-[11px]">
                        {getSourceIcon(pt.source)}
                        <span>{pt.source}</span>
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                      {pt.agent_id || 'System Generated'}
                    </td>

                    <td className="py-3 px-4 text-right font-mono text-slate-400 text-[11px]">
                      {pt.event_at}
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
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} commitments
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
