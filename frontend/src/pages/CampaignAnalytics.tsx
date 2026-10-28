import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { CampaignItem } from '../types';
import {
  Megaphone, Search, Filter, RefreshCw,
  ChevronLeft, ChevronRight, BarChart3, Layers, Target
} from 'lucide-react';

export const CampaignAnalytics: React.FC = () => {
  const [items, setItems] = useState<CampaignItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [channel, setChannel] = useState('');
  const [strategy, setStrategy] = useState('');

  const loadData = () => {
    setLoading(true);
    Promise.all([
      apiClient.getCampaigns({
        channel: channel || undefined,
        strategy_version: strategy || undefined,
        page,
        page_size: pageSize
      }),
      apiClient.getCampaignSummary()
    ])
      .then(([cRes, sRes]) => {
        setItems(cRes.items);
        setTotal(cRes.total);
        setSummary(sRes);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [page, channel, strategy]);

  const totalPages = Math.ceil(total / pageSize) || 1;

  const getChannelBadge = (ch: string) => {
    switch (ch.toUpperCase()) {
      case 'FIELD': return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
      case 'MIXED': return 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30';
      case 'VOICE': return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
      case 'WHATSAPP': return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'SMS': return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      default: return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Megaphone className="w-5 h-5 text-indigo-400" />
            Campaign Analytics & Strategy Versioning
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Tracking 120 collection campaigns across omnichannel routes (Field, Voice, SMS, WhatsApp, Mixed) and target cohort definitions.
          </p>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block">Total Active Campaigns</span>
          <span className="font-mono text-lg font-bold text-white">
            {summary?.total_campaigns || '120'} Campaigns
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Strategy Filters
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={channel}
            onChange={(e) => { setChannel(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Channels</option>
            <option value="FIELD">Field Ops</option>
            <option value="MIXED">Mixed Omnichannel</option>
            <option value="VOICE">Voice Outreach</option>
            <option value="WHATSAPP">WhatsApp</option>
            <option value="SMS">SMS Notice</option>
          </select>

          <select
            value={strategy}
            onChange={(e) => { setStrategy(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Strategy Versions</option>
            <option value="v1">Strategy v1</option>
            <option value="v2">Strategy v2</option>
            <option value="v3">Strategy v3</option>
            <option value="legacy">Legacy Strategy</option>
          </select>

          <button
            onClick={loadData}
            title="Refresh Campaigns"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Campaigns Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Campaign ID & Name</th>
                <th className="py-3 px-4 font-semibold">Channel</th>
                <th className="py-3 px-4 font-semibold">Strategy Version</th>
                <th className="py-3 px-4 font-semibold">Target Criteria</th>
                <th className="py-3 px-4 font-semibold">Targeted Cohort</th>
                <th className="py-3 px-4 font-semibold">Outreach Actions</th>
                <th className="py-3 px-4 font-semibold">Engagement Rate</th>
                <th className="py-3 px-4 font-semibold text-right">Window</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Fetching campaign performance metrics...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No campaigns match current filters.
                  </td>
                </tr>
              ) : (
                items.map((c) => (
                  <tr key={c.campaign_id} className="hover:bg-slate-800/40 transition-colors">

                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{c.campaign_name}</div>
                      <div className="font-mono text-[10px] text-slate-400">{c.campaign_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getChannelBadge(c.channel)}`}>
                        {c.channel}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                        {c.strategy_version}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-300">
                      {c.target_definition || 'All DPD Buckets'}
                    </td>

                    <td className="py-3 px-4 font-mono font-bold text-white">
                      {c.targeted_accounts.toLocaleString()}
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-300">
                      {c.outreach_events.toLocaleString()}
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-indigo-400">{c.engagement_rate_pct}%</span>
                        <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.min(100, c.engagement_rate_pct)}%` }} />
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-right font-mono text-slate-400 text-[11px]">
                      {c.start_at ? c.start_at.substring(0, 10) : 'Active'}
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
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} campaigns
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
