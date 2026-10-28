import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { AgentItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  UserCheck, Search, Filter, PhoneCall,
  TrendingUp, Award, ChevronLeft, ChevronRight, RefreshCw
} from 'lucide-react';

export const AgentPerformance: React.FC = () => {
  const [items, setItems] = useState<AgentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [team, setTeam] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');

  const loadAgents = () => {
    setLoading(true);
    apiClient.getAgents({
      team: team || undefined,
      status: status || undefined,
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
    loadAgents();
  }, [page, team, status]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadAgents();
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-indigo-400" />
            Agent Performance & Productivity Scorecards
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Activity tracking across 1,000 canonical recovery agents, contact rates, call handling duration, and PTP conversion efficiency.
          </p>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block">Total Active Fleet</span>
          <span className="font-mono text-lg font-bold text-white">1,000 Agents</span>
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
              placeholder="Search Agent Name, ID, EMP Code..."
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
            value={team}
            onChange={(e) => { setTeam(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Operational Teams</option>
            <option value="T1">Team 1 (T1)</option>
            <option value="T2">Team 2 (T2)</option>
            <option value="T3">Team 3 (T3)</option>
            <option value="DIGITAL">Digital Recovery</option>
            <option value="FIELD">Field Operations</option>
          </select>

          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
            <option value="SUSPENDED">Suspended</option>
          </select>

          <button
            onClick={loadAgents}
            title="Refresh Agents"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>

      </div>

      {/* Agents Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Agent Profile</th>
                <th className="py-3 px-4 font-semibold">Team & Vendor</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Calls Handled</th>
                <th className="py-3 px-4 font-semibold">Contact Rate</th>
                <th className="py-3 px-4 font-semibold">Avg Handle Time</th>
                <th className="py-3 px-4 font-semibold">PTP Conversion</th>
                <th className="py-3 px-4 font-semibold text-right">Promised Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Calculating agent productivity scorecards...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No agents match current filters.
                  </td>
                </tr>
              ) : (
                items.map((agt) => (
                  <tr key={agt.agent_id} className="hover:bg-slate-800/40 transition-colors">

                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{agt.agent_name}</div>
                      <div className="font-mono text-[10px] text-slate-400">{agt.agent_id} • {agt.employee_code}</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-medium text-slate-300">{agt.team || 'Unassigned'}</span>
                      <div className="text-[10px] text-slate-500 font-mono">{agt.vendor_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <StatusBadge status={agt.status} />
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-white">{agt.total_calls.toLocaleString()}</div>
                      <div className="text-[10px] text-slate-400">{agt.answered_calls} answered</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-indigo-400">{agt.contact_rate_pct}%</span>
                        <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.min(100, agt.contact_rate_pct)}%` }} />
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-300">
                      {agt.avg_call_duration_sec}s
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-emerald-400">
                        {agt.ptp_conversion_rate_pct}%
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {agt.kept_ptp} kept of {agt.total_ptp_secured}
                      </div>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <span className="font-mono font-bold text-white text-sm">
                        ₹{agt.total_promised_amount.toLocaleString()}
                      </span>
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
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} agents
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
