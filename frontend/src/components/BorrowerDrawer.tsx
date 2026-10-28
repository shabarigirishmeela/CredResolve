import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { StatusBadge } from './StatusBadge';
import { PriorityBadge } from './PriorityBadge';
import { 
  X, User, CreditCard, Receipt, PhoneCall, 
  CalendarCheck, ShieldAlert, MapPin, Loader2 
} from 'lucide-react';

interface BorrowerDrawerProps {
  borrowerId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const BorrowerDrawer: React.FC<BorrowerDrawerProps> = ({ borrowerId, isOpen, onClose }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'accounts' | 'payments' | 'calls' | 'ptps' | 'complaints' | 'visits'>('accounts');

  useEffect(() => {
    if (borrowerId && isOpen) {
      setLoading(true);
      apiClient.getBorrowerDetail(borrowerId)
        .then(res => setData(res))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    } else {
      setData(null);
    }
  }, [borrowerId, isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end animate-fadeIn">
      <div className="relative w-full max-w-2xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-900/90 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-indigo-500/20">
              {data ? data.name[0] : <User className="w-6 h-6" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                {data ? data.name : 'Loading Borrower...'}
                {data && (
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {data.borrower_id}
                  </span>
                )}
              </h2>
              {data && (
                <div className="flex flex-wrap gap-2 text-xs text-slate-400 mt-1">
                  <span>{data.city}, {data.state}</span>
                  <span>•</span>
                  <span>{data.phone_masked}</span>
                  <span>•</span>
                  <span>{data.email_masked}</span>
                </div>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6 gap-2 overflow-x-auto text-xs font-medium">
          {[
            { id: 'accounts', label: 'Accounts', icon: <CreditCard className="w-3.5 h-3.5" />, count: data?.accounts?.length },
            { id: 'payments', label: 'Payments', icon: <Receipt className="w-3.5 h-3.5" />, count: data?.payments?.length },
            { id: 'calls', label: 'Calls', icon: <PhoneCall className="w-3.5 h-3.5" />, count: data?.calls?.length },
            { id: 'ptps', label: 'PTPs', icon: <CalendarCheck className="w-3.5 h-3.5" />, count: data?.ptps?.length },
            { id: 'complaints', label: 'Grievances', icon: <ShieldAlert className="w-3.5 h-3.5" />, count: data?.complaints?.length },
            { id: 'visits', label: 'Field Visits', icon: <MapPin className="w-3.5 h-3.5" />, count: data?.field_visits?.length }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 py-3 px-3 border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id 
                  ? 'border-indigo-500 text-indigo-400' 
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
              <span className="text-xs">Fetching 360-degree borrower profile...</span>
            </div>
          ) : !data ? (
            <div className="text-center py-12 text-slate-500 text-xs">No borrower records selected.</div>
          ) : (
            <div>
              {/* Accounts Tab */}
              {activeTab === 'accounts' && (
                <div className="space-y-4">
                  {data.accounts.map((acc: any) => (
                    <div key={acc.account_id} className="p-4 rounded-xl border border-slate-800 bg-slate-800/40 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-sm font-semibold text-white">{acc.account_id}</span>
                        <div className="flex items-center gap-2">
                          <StatusBadge status={acc.status} />
                          <PriorityBadge tier={acc.priority_tier} score={acc.priority_score} size="sm" />
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800/50">
                        <div>
                          <span className="text-slate-500 block">Loan Product</span>
                          <span className="font-medium text-slate-200">{acc.loan_type}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Outstanding</span>
                          <span className="font-mono font-bold text-amber-400">₹{acc.outstanding_amount.toLocaleString()}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Days Past Due</span>
                          <span className="font-mono font-bold text-rose-400">{acc.dpd} DPD</span>
                        </div>
                      </div>
                      <div className="text-xs text-slate-400 flex items-center justify-between">
                        <span>Action: <strong className="text-indigo-400">{acc.recommended_action}</strong></span>
                        {acc.compliance_hold && (
                          <span className="text-rose-400 font-medium">Compliance Hold Active</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Payments Tab */}
              {activeTab === 'payments' && (
                <div className="space-y-3">
                  {data.payments.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs">No payment events recorded.</div>
                  ) : (
                    data.payments.map((p: any) => (
                      <div key={p.payment_id} className="p-3 rounded-lg border border-slate-800 bg-slate-800/30 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-mono font-semibold text-slate-200">{p.payment_id}</div>
                          <div className="text-slate-500">{p.event_at} • {p.payment_method}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono font-bold text-white text-sm">₹{p.amount.toLocaleString()}</div>
                          <StatusBadge status={p.payment_status} />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Calls Tab */}
              {activeTab === 'calls' && (
                <div className="space-y-3">
                  {data.calls.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs">No call interactions logged.</div>
                  ) : (
                    data.calls.map((c: any) => (
                      <div key={c.call_id} className="p-3 rounded-lg border border-slate-800 bg-slate-800/30 flex items-center justify-between text-xs">
                        <div>
                          <span className="font-mono font-medium text-slate-300">{c.call_id}</span>
                          <div className="text-slate-500">{c.event_at} • {c.direction} ({c.duration_sec}s)</div>
                        </div>
                        <StatusBadge status={c.call_status} />
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* PTPs Tab */}
              {activeTab === 'ptps' && (
                <div className="space-y-3">
                  {data.ptps.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs">No promise-to-pay records found.</div>
                  ) : (
                    data.ptps.map((pt: any) => (
                      <div key={pt.ptp_id} className="p-3 rounded-lg border border-slate-800 bg-slate-800/30 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-mono font-medium text-slate-300">{pt.ptp_id}</div>
                          <div className="text-slate-500">Promised Date: {pt.promised_date} ({pt.source})</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono font-bold text-white">₹{pt.promised_amount.toLocaleString()}</div>
                          <StatusBadge status={pt.status} />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Complaints Tab */}
              {activeTab === 'complaints' && (
                <div className="space-y-3">
                  {data.complaints.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs">No complaints or disputes filed.</div>
                  ) : (
                    data.complaints.map((cm: any) => (
                      <div key={cm.complaint_id} className="p-3.5 rounded-xl border border-rose-500/20 bg-rose-500/5 space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-semibold text-rose-300">{cm.complaint_id}</span>
                          <div className="flex gap-1.5">
                            <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-semibold">{cm.severity}</span>
                            <StatusBadge status={cm.status} />
                          </div>
                        </div>
                        <div className="text-slate-300">Type: <strong>{cm.complaint_type}</strong> via {cm.source}</div>
                        <div className="text-slate-500 text-[11px]">Logged: {cm.event_at}</div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Field Visits Tab */}
              {activeTab === 'visits' && (
                <div className="space-y-3">
                  {data.field_visits.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-xs">No on-ground field visits conducted.</div>
                  ) : (
                    data.field_visits.map((v: any) => (
                      <div key={v.visit_id} className="p-3 rounded-lg border border-slate-800 bg-slate-800/30 flex items-center justify-between text-xs">
                        <div>
                          <span className="font-mono font-medium text-slate-300">{v.visit_id}</span>
                          <div className="text-slate-500">{v.event_at} • {v.visit_type}</div>
                        </div>
                        <StatusBadge status={v.outcome} />
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close 360° Profile
          </button>
        </div>

      </div>
    </div>
  );
};
