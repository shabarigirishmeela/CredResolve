import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import {
  PhoneCall, MessageSquare, Smartphone, ChevronLeft,
  ChevronRight, RefreshCw, Send, CheckCircle2, MousePointer
} from 'lucide-react';

export const CommunicationAnalytics: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'calls' | 'sms' | 'whatsapp'>('calls');
  const [summary, setSummary] = useState<any>(null);

  // Data for active tab
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');

  const loadSummary = () => {
    apiClient.getCommunicationsSummary()
      .then(res => setSummary(res))
      .catch(err => console.error(err));
  };

  const loadTabItems = () => {
    setLoading(true);
    let fetchPromise;
    if (activeTab === 'calls') {
      fetchPromise = apiClient.getCalls({ status: statusFilter || undefined, page, page_size: pageSize });
    } else if (activeTab === 'sms') {
      fetchPromise = apiClient.getSms({ event_type: statusFilter || undefined, page, page_size: pageSize });
    } else {
      fetchPromise = apiClient.getWhatsapp({ event_type: statusFilter || undefined, page, page_size: pageSize });
    }

    fetchPromise
      .then(res => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    setPage(1);
    setStatusFilter('');
  }, [activeTab]);

  useEffect(() => {
    loadTabItems();
  }, [activeTab, page, statusFilter]);

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <PhoneCall className="w-5 h-5 text-indigo-400" />
            Omnichannel Communication Analytics
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time delivery funnels, borrower engagement telemetry, and failure tracking across Voice, SMS, and WhatsApp channels.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300">
          <span>Calls: 90k • WhatsApp: 60k • SMS: 45k</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Voice Contact Rate"
          value={`${summary?.calls?.contact_rate_pct || 0}%`}
          subtitle={`${summary?.calls?.answered?.toLocaleString() || 0} Connected Calls`}
          change="Live Agent Reach"
          isPositive={true}
          icon={<PhoneCall className="w-5 h-5 text-blue-400" />}
          variant="default"
        />

        <MetricCard
          title="WhatsApp Payment Clicks"
          value={summary?.whatsapp?.payment_clicks?.toLocaleString() || '0'}
          subtitle={`Payment Intent Rate: ${summary?.whatsapp?.payment_intent_rate_pct || 0}%`}
          change="Direct Resolution"
          isPositive={true}
          icon={<MousePointer className="w-5 h-5 text-emerald-400" />}
          variant="success"
        />

        <MetricCard
          title="SMS Delivery Rate"
          value={`${summary?.sms?.delivery_rate_pct || 0}%`}
          subtitle={`${summary?.sms?.clicked?.toLocaleString() || 0} Clicks on Payment Link`}
          change="Clean Delivery"
          isPositive={true}
          icon={<Smartphone className="w-5 h-5 text-amber-400" />}
          variant="warning"
        />

        <MetricCard
          title="WhatsApp Delivery Rate"
          value={`${summary?.whatsapp?.delivery_rate_pct || 0}%`}
          subtitle={`${summary?.whatsapp?.replies?.toLocaleString() || 0} Inbound Replies Received`}
          change="Interactive Channel"
          isPositive={true}
          icon={<MessageSquare className="w-5 h-5 text-indigo-400" />}
          variant="purple"
        />
      </div>

      {/* Channel Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('calls')}
          className={`flex items-center gap-2 py-3 px-5 border-b-2 text-xs font-semibold transition-colors ${
            activeTab === 'calls'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <PhoneCall className="w-4 h-4" />
          <span>Voice Calls ({summary?.calls?.total?.toLocaleString() || '90,000'})</span>
        </button>

        <button
          onClick={() => setActiveTab('whatsapp')}
          className={`flex items-center gap-2 py-3 px-5 border-b-2 text-xs font-semibold transition-colors ${
            activeTab === 'whatsapp'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>WhatsApp Events ({summary?.whatsapp?.total?.toLocaleString() || '60,000'})</span>
        </button>

        <button
          onClick={() => setActiveTab('sms')}
          className={`flex items-center gap-2 py-3 px-5 border-b-2 text-xs font-semibold transition-colors ${
            activeTab === 'sms'
              ? 'border-amber-500 text-amber-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Smartphone className="w-4 h-4" />
          <span>SMS Events ({summary?.sms?.total?.toLocaleString() || '45,000'})</span>
        </button>
      </div>

      {/* Events Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              {activeTab === 'calls' ? (
                <tr>
                  <th className="py-3 px-4 font-semibold">Call ID</th>
                  <th className="py-3 px-4 font-semibold">Account & Borrower</th>
                  <th className="py-3 px-4 font-semibold">Agent / Dialer</th>
                  <th className="py-3 px-4 font-semibold">Direction</th>
                  <th className="py-3 px-4 font-semibold">Call Status</th>
                  <th className="py-3 px-4 font-semibold">Duration</th>
                  <th className="py-3 px-4 font-semibold text-right">Event Timestamp</th>
                </tr>
              ) : (
                <tr>
                  <th className="py-3 px-4 font-semibold">Event ID</th>
                  <th className="py-3 px-4 font-semibold">Account & Borrower</th>
                  <th className="py-3 px-4 font-semibold">Message ID</th>
                  <th className="py-3 px-4 font-semibold">Event Type</th>
                  <th className="py-3 px-4 font-semibold">Template Code</th>
                  <th className="py-3 px-4 font-semibold text-right">Event Timestamp</th>
                </tr>
              )}
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Fetching communication events...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No communication events found.
                  </td>
                </tr>
              ) : (
                items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                    {activeTab === 'calls' ? (
                      <>
                        <td className="py-3 px-4 font-mono font-bold text-white">{item.call_id}</td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          <div>{item.account_id}</div>
                          <div className="text-[10px] text-slate-500">{item.borrower_id}</div>
                        </td>
                        <td className="py-3 px-4 text-slate-300">{item.agent_id}</td>
                        <td className="py-3 px-4 text-slate-400">{item.direction}</td>
                        <td className="py-3 px-4"><StatusBadge status={item.call_status} /></td>
                        <td className="py-3 px-4 font-mono text-slate-300">{item.duration_sec}s</td>
                        <td className="py-3 px-4 text-right font-mono text-slate-400 text-[11px]">{item.event_at}</td>
                      </>
                    ) : (
                      <>
                        <td className="py-3 px-4 font-mono font-bold text-white">
                          {activeTab === 'sms' ? item.sms_event_id : item.whatsapp_event_id}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          <div>{item.account_id}</div>
                          <div className="text-[10px] text-slate-500">{item.borrower_id}</div>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400">{item.message_id}</td>
                        <td className="py-3 px-4"><StatusBadge status={item.event_type} /></td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                            {item.template_code}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-400 text-[11px]">{item.event_at}</td>
                      </>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} events
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
