import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { ComplaintItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import {
  ShieldAlert, CheckCircle2, AlertTriangle, Scale,
  Search, ChevronLeft, ChevronRight, RefreshCw, X
} from 'lucide-react';

export const ComplaintsCompliance: React.FC = () => {
  const [items, setItems] = useState<ComplaintItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [severity, setSeverity] = useState('');
  const [status, setStatus] = useState('');
  const [complaintType, setComplaintType] = useState('');
  const [search, setSearch] = useState('');

  // Resolve Modal State
  const [resolveModalOpen, setResolveModalOpen] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState<ComplaintItem | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      apiClient.getComplaints({
        severity: severity || undefined,
        status: status || undefined,
        complaint_type: complaintType || undefined,
        search: search || undefined,
        page,
        page_size: pageSize
      }),
      apiClient.getComplaintsSummary()
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
  }, [page, severity, status, complaintType]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const handleOpenResolve = (c: ComplaintItem) => {
    setSelectedComplaint(c);
    setResolutionNotes(`Grievance regarding ${c.complaint_type} reviewed by Compliance Ombudsman. Settlement/cure agreement reached.`);
    setResolveModalOpen(true);
  };

  const handleSubmitResolve = async () => {
    if (!selectedComplaint) return;
    try {
      const res = await apiClient.resolveComplaint(selectedComplaint.complaint_id, resolutionNotes);
      setResolveModalOpen(false);
      setActionSuccessMsg(
        res.compliance_hold_cleared
          ? `Grievance ${selectedComplaint.complaint_id} resolved! Compliance hold automatically cleared on account ${res.account_id}.`
          : `Grievance ${selectedComplaint.complaint_id} marked as resolved.`
      );
      loadData();
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err) {
      console.error(err);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-rose-500/20 bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold mb-2">
            <Scale className="w-3.5 h-3.5" />
            Fair Practices Code & Consumer Protection Compliance
          </div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            Complaints, Grievances & Regulatory Dispute Tracking
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Active dispute surveillance. Critical severity complaints automatically enforce collection pauses to uphold RBI guidelines and prevent aggressive or non-compliant outreach.
          </p>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block">Total Grievances</span>
          <span className="font-mono text-lg font-bold text-white">
            {summary?.total_complaints?.toLocaleString() || '8,000'}
          </span>
        </div>
      </div>

      {actionSuccessMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Registered Complaints"
          value={summary?.total_complaints?.toLocaleString() || '8,000'}
          subtitle="All Channels (Call, Field, Web)"
          icon={<ShieldAlert className="w-5 h-5 text-blue-400" />}
          variant="default"
        />

        <MetricCard
          title="Open / Under Investigation"
          value={summary?.open_unresolved?.toLocaleString() || '0'}
          subtitle="Collection Outreach Paused"
          change="Urgent Review"
          isPositive={false}
          icon={<AlertTriangle className="w-5 h-5 text-rose-400" />}
          variant="danger"
        />

        <MetricCard
          title="Resolved & Closed"
          value={summary?.resolved_closed?.toLocaleString() || '0'}
          subtitle="Borrower Cured / Closed"
          change="Audited"
          isPositive={true}
          icon={<CheckCircle2 className="w-5 h-5 text-emerald-400" />}
          variant="success"
        />

        <MetricCard
          title="Resolution Rate"
          value={`${summary?.resolution_rate_pct || 0}%`}
          subtitle="Regulatory Standard Target > 90%"
          change="Compliance Metric"
          isPositive={true}
          icon={<Scale className="w-5 h-5 text-indigo-400" />}
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
              placeholder="Search Complaint ID, Account..."
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
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical (Harassment / Ombudsman)</option>
            <option value="HIGH">High Severity</option>
            <option value="MEDIUM">Medium Severity</option>
            <option value="LOW">Low Severity</option>
          </select>

          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Dispute Statuses</option>
            <option value="OPEN">Open (Active Pause)</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            value={complaintType}
            onChange={(e) => { setComplaintType(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">All Complaint Types</option>
            <option value="HARASSMENT">Harassment</option>
            <option value="DISPUTE">Loan Balance Dispute</option>
            <option value="PRIVACY">Privacy Breach</option>
            <option value="DND">DND Violation</option>
            <option value="AGENT_BEHAVIOUR">Agent Misbehavior</option>
            <option value="PAYMENT">Payment Mismatch</option>
            <option value="WRONG_CONTACT">Wrong Contact</option>
          </select>

          <button
            onClick={loadData}
            title="Refresh Complaints"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>

      </div>

      {/* Complaints Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Complaint ID</th>
                <th className="py-3 px-4 font-semibold">Account & Borrower</th>
                <th className="py-3 px-4 font-semibold">Grievance Type</th>
                <th className="py-3 px-4 font-semibold">Severity</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Source</th>
                <th className="py-3 px-4 font-semibold">Incident Date</th>
                <th className="py-3 px-4 font-semibold text-right">Regulatory Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Auditing grievance cases...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No complaints match current filters.
                  </td>
                </tr>
              ) : (
                items.map((c) => (
                  <tr key={c.complaint_id} className="hover:bg-slate-800/40 transition-colors">

                    <td className="py-3 px-4 font-mono font-bold text-white">
                      {c.complaint_id}
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono text-slate-300">{c.account_id}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{c.borrower_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-medium text-slate-200">{c.complaint_type}</span>
                    </td>

                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded font-bold text-[11px] ${
                        c.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                        c.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      }`}>
                        {c.severity}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <StatusBadge status={c.status} />
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                      {c.source}
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                      {c.event_at}
                    </td>

                    <td className="py-3 px-4 text-right">
                      {c.status !== 'RESOLVED' && c.status !== 'CLOSED' ? (
                        <button
                          onClick={() => handleOpenResolve(c)}
                          className="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 transition-all shadow-sm"
                        >
                          Resolve Grievance
                        </button>
                      ) : (
                        <span className="text-slate-500 text-[11px] font-mono">
                          Resolved {c.resolution_at ? c.resolution_at.substring(0, 10) : ''}
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
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} complaints
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

      {/* Resolve Grievance Modal */}
      {resolveModalOpen && selectedComplaint && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">

            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 py-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Resolve Grievance & Lift Pause</h3>
                  <p className="text-xs text-slate-400 font-mono">{selectedComplaint.complaint_id} • {selectedComplaint.account_id}</p>
                </div>
              </div>
              <button
                onClick={() => setResolveModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-800/40 space-y-1">
                <span className="text-slate-400">Complaint Details:</span>
                <div className="font-semibold text-white text-sm">
                  {selectedComplaint.complaint_type} ({selectedComplaint.severity} Severity)
                </div>
                <div className="text-slate-400">Source: {selectedComplaint.source} on {selectedComplaint.event_at}</div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">
                  Resolution Notes & Audit Trail
                </label>
                <textarea
                  rows={4}
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  className="w-full p-3 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="text-[11px] text-amber-400/90 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-lg">
                Note: If this account has no other open critical complaints, resolving this complaint will automatically lift the compliance hold and re-enable standard collection outreach.
              </div>
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex justify-end gap-2">
              <button
                onClick={() => setResolveModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitResolve}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition-colors"
              >
                Confirm Resolution
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
