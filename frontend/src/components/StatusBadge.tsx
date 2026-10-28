import React from 'react';

interface StatusBadgeProps {
  status: string;
  type?: 'account' | 'payment' | 'ptp' | 'complaint' | 'generic';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type: _type = 'generic' }) => {
  const s = status ? status.toUpperCase() : 'UNKNOWN';

  const getStyle = () => {
    // Payments
    if (s === 'SUCCESS' || s === 'PAID' || s === 'KEPT' || s === 'RESOLVED') {
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    }
    if (s === 'FAILED' || s === 'BROKEN' || s === 'WRITEOFF' || s === 'CRITICAL') {
      return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
    }
    if (s === 'PENDING' || s === 'OPEN' || s === 'INVESTIGATING' || s === 'DELINQUENT' || s === 'HIGH') {
      return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
    }
    if (s === 'REVERSED' || s === 'CANCELLED' || s === 'SUSPENDED') {
      return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
    }
    if (s === 'ACTIVE' || s === 'CONNECTED' || s === 'ANSWERED') {
      return 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30';
    }
    if (s === 'CLOSED' || s === 'INACTIVE' || s === 'NO_ANSWER') {
      return 'bg-slate-700/50 text-slate-400 border-slate-600/40';
    }
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getStyle()}`}>
      {s.replace(/_/g, ' ')}
    </span>
  );
};
