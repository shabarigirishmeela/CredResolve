import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: string;
  isPositive?: boolean;
  icon: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'purple';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  change,
  isPositive,
  icon,
  variant = 'default'
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return 'from-emerald-500/10 via-slate-900 to-slate-900/80 border-emerald-500/20 text-emerald-400';
      case 'warning':
        return 'from-amber-500/10 via-slate-900 to-slate-900/80 border-amber-500/20 text-amber-400';
      case 'danger':
        return 'from-rose-500/10 via-slate-900 to-slate-900/80 border-rose-500/20 text-rose-400';
      case 'purple':
        return 'from-indigo-500/10 via-slate-900 to-slate-900/80 border-indigo-500/20 text-indigo-400';
      default:
        return 'from-blue-500/10 via-slate-900 to-slate-900/80 border-slate-800 text-blue-400';
    }
  };

  return (
    <div className={`relative overflow-hidden rounded-xl border bg-gradient-to-b p-5 transition-all duration-200 hover:border-slate-700/80 hover:shadow-lg ${getVariantStyles()}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/50">
          {icon}
        </div>
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold tracking-tight text-white font-mono">
          {value}
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs">
          {change && (
            <span className={`font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
              {change}
            </span>
          )}
          {subtitle && (
            <span className="text-slate-400 truncate">
              {subtitle}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
