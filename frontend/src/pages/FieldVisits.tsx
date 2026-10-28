import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { FieldVisitItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import {
  MapPin, CheckCircle, Navigation, Search,
  Filter, ChevronLeft, ChevronRight, RefreshCw, Compass
} from 'lucide-react';

export const FieldVisits: React.FC = () => {
  const [items, setItems] = useState<FieldVisitItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [outcome, setOutcome] = useState('');
  const [visitType, setVisitType] = useState('');
  const [search, setSearch] = useState('');

  const loadData = () => {
    setLoading(true);
    Promise.all([
      apiClient.getFieldVisits({
        outcome: outcome || undefined,
        visit_type: visitType || undefined,
        search: search || undefined,
        page,
        page_size: pageSize
      }),
      apiClient.getFieldVisitSummary()
    ])
      .then(([vRes, sRes]) => {
        setItems(vRes.items);
        setTotal(vRes.total);
        setSummary(sRes);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [page, outcome, visitType]);

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
            <MapPin className="w-5 h-5 text-indigo-400" />
            Field Visit Operations & Physical Verification
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Tracking 25,000 on-ground visits, GPS coordinate validation, visit outcomes, and borrower physical contact rate.
          </p>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block">Total Field Visits</span>
          <span className="font-mono text-lg font-bold text-white">
            {summary?.total_visits?.toLocaleString() || '25,000'}
          </span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          title="Total Field Dispatches"
          value={summary?.total_visits?.toLocaleString() || '25,000'}
          subtitle="Physical In-Person Verification"
          icon={<Compass className="w-5 h-5 text-blue-400" />}
          variant="default"
        />

        <MetricCard
          title="Physical Contact Rate"
          value={`${summary?.contact_success_rate_pct || 0}%`}
          subtitle="Contacted / Paid / PTP"
          change="Success Rate"
          isPositive={true}
          icon={<CheckCircle className="w-5 h-5 text-emerald-400" />}
          variant="success"
        />

        <MetricCard
          title="Direct Payments & PTPs"
          value="8,280"
          subtitle="Realized on Field Visit"
          change="High Conversion"
          isPositive={true}
          icon={<Navigation className="w-5 h-5 text-purple-400" />}
          variant="purple"
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
              placeholder="Search Visit ID, Account, Agent..."
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
            value={outcome}
            onChange={(e) => { setOutcome(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Visit Outcomes</option>
            <option value="PAID">Paid on Site</option>
            <option value="PTP">PTP Secured</option>
            <option value="CONTACTED">Borrower Contacted</option>
            <option value="NOT_AVAILABLE">Not Available / Door Locked</option>
            <option value="REFUSED">Refused Payment</option>
            <option value="WRONG_ADDRESS">Wrong Address / Shifted</option>
          </select>

          <select
            value={visitType}
            onChange={(e) => { setVisitType(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Visit Types</option>
            <option value="FIRST_VISIT">First Visit</option>
            <option value="FOLLOWUP">Follow-up</option>
            <option value="NOTICE">Formal Notice Delivery</option>
            <option value="AFTER_HOURS">After-Hours Visit</option>
          </select>

          <button
            onClick={loadData}
            title="Refresh Field Visits"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>

      </div>

      {/* Field Visits Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Visit ID</th>
                <th className="py-3 px-4 font-semibold">Account & Borrower</th>
                <th className="py-3 px-4 font-semibold">Field Agent</th>
                <th className="py-3 px-4 font-semibold">Visit Type</th>
                <th className="py-3 px-4 font-semibold">Outcome</th>
                <th className="py-3 px-4 font-semibold">GPS Location</th>
                <th className="py-3 px-4 font-semibold text-right">Event Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Fetching field visits...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No field visits match current filters.
                  </td>
                </tr>
              ) : (
                items.map((v) => (
                  <tr key={v.visit_id} className="hover:bg-slate-800/40 transition-colors">

                    <td className="py-3 px-4 font-mono font-bold text-white">
                      {v.visit_id}
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono text-slate-300">{v.account_id}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{v.borrower_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-200">{v.agent_name}</div>
                      <div className="font-mono text-[10px] text-slate-500">{v.agent_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]">
                        {v.visit_type}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <StatusBadge status={v.outcome} />
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                      {v.latitude && v.longitude ? `${v.latitude}, ${v.longitude}` : 'Pending Fix'}
                    </td>

                    <td className="py-3 px-4 text-right font-mono text-slate-400 text-[11px]">
                      {v.event_at}
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
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} visits
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
