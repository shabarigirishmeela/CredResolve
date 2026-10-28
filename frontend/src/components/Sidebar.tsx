import React from 'react';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, Sparkles, Users, CreditCard,
  Receipt, CalendarCheck2, UserCheck, Megaphone,
  PhoneCall, MapPin, ShieldAlert, FileSpreadsheet,
  FileText, Settings, LogOut
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const { user, logout } = useAuth();

  const navItems = [
    { id: 'dashboard', label: 'Executive Dashboard', icon: <LayoutDashboard className="w-4 h-4" />, badge: 'Realtime' },
    { id: 'work-queue', label: 'Work Queue (Prioritized)', icon: <Sparkles className="w-4 h-4 text-amber-400" />, badge: 'AI Engine' },
    { id: 'borrowers', label: 'Borrower Directory', icon: <Users className="w-4 h-4" /> },
    { id: 'accounts', label: 'Account Portfolio', icon: <CreditCard className="w-4 h-4" /> },
    { id: 'payments', label: 'Payment Transactions', icon: <Receipt className="w-4 h-4" /> },
    { id: 'ptp', label: 'Promises to Pay (PTP)', icon: <CalendarCheck2 className="w-4 h-4" /> },
    { id: 'agents', label: 'Agent Performance', icon: <UserCheck className="w-4 h-4" /> },
    { id: 'campaigns', label: 'Campaign Analytics', icon: <Megaphone className="w-4 h-4" /> },
    { id: 'communications', label: 'Omnichannel Comms', icon: <PhoneCall className="w-4 h-4" /> },
    { id: 'field-visits', label: 'Field Visit Ops', icon: <MapPin className="w-4 h-4" /> },
    { id: 'complaints', label: 'Complaints & Compliance', icon: <ShieldAlert className="w-4 h-4 text-rose-400" />, badge: 'Fair Code' },
    { id: 'data-quality', label: 'Data Quality & Pipeline', icon: <FileSpreadsheet className="w-4 h-4 text-emerald-400" /> },
    { id: 'reports', label: 'Reports & Exports', icon: <FileText className="w-4 h-4" /> },
    { id: 'settings', label: 'Engine Settings', icon: <Settings className="w-4 h-4" /> }
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col h-screen shrink-0 select-none">

      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-600 to-cyan-400 flex items-center justify-center text-white font-black text-xl shadow-lg shadow-indigo-500/25">
          CR
        </div>
        <div>
          <h1 className="text-sm font-bold text-white tracking-tight flex items-center gap-1.5">
            CredResolve
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Intel
            </span>
          </h1>
          <p className="text-[11px] text-slate-400">AI Recovery Platform</p>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3 mb-2">
          Operations & Intelligence
        </div>
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
                  : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-2.5 truncate">
                <span className={isActive ? 'text-indigo-400' : 'text-slate-400'}>
                  {item.icon}
                </span>
                <span className="truncate">{item.label}</span>
              </div>
              {item.badge && (
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                  isActive ? 'bg-indigo-500/30 text-indigo-200' : 'bg-slate-800 text-slate-400'
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* User Card & Logout */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60">
        <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-900 border border-slate-800">
          <div className="flex items-center gap-2.5 truncate">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-300">
              {user ? user.full_name[0] : 'U'}
            </div>
            <div className="truncate text-left">
              <div className="text-xs font-semibold text-slate-200 truncate">
                {user ? user.full_name : 'Guest User'}
              </div>
              <div className="text-[10px] text-indigo-400 uppercase font-mono tracking-wider">
                {user ? user.role : 'Offline'}
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log Out"
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-rose-400 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

    </aside>
  );
};
