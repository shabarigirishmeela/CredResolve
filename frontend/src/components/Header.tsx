import React from 'react';
import { ShieldCheck, Clock, Database } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 flex items-center justify-between shrink-0 sticky top-0 z-30">

      {/* Title & Subtitle */}
      <div>
        <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
          {title}
        </h2>
        {subtitle && (
          <p className="text-xs text-slate-400">{subtitle}</p>
        )}
      </div>

      {/* Badges & System Status */}
      <div className="flex items-center gap-3 text-xs">

        {/* Compliance Guardrail Indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 font-medium">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>RBI Fair Practices Guardrail: ON</span>
        </div>

        {/* Database Live Sync */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700/60 text-slate-300 font-mono text-[11px]">
          <Database className="w-3.5 h-3.5 text-indigo-400" />
          <span>credresolve.db (30k Core)</span>
        </div>

        {/* Contact Window Indicator */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700/60 text-slate-300 text-[11px]">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span>Permitted Hours: 08:00 – 19:00</span>
        </div>

      </div>

    </header>
  );
};
