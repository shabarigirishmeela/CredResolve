import React from 'react';

interface PriorityBadgeProps {
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  score?: number;
  size?: 'sm' | 'md' | 'lg';
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ tier, score, size = 'md' }) => {
  const getStyles = () => {
    switch (tier.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30 shadow-[0_0_12px_rgba(244,63,94,0.25)]';
      case 'HIGH':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30 shadow-[0_0_10px_rgba(245,158,11,0.2)]';
      case 'MEDIUM':
        return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
      case 'LOW':
      default:
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    }
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5'
  };

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${getStyles()} ${sizeClasses[size]}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      <span>{tier}</span>
      {score !== undefined && (
        <span className="opacity-80 font-mono text-[10px] bg-black/30 px-1.5 py-0.2 rounded">
          {score.toFixed(0)}
        </span>
      )}
    </span>
  );
};
