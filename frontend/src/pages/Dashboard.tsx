import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { DashboardData } from '../types';
import { MetricCard } from '../components/MetricCard';
import {
  DollarSign, AlertTriangle, TrendingUp,
  CalendarCheck, Filter, RefreshCw,
  CreditCard, Flame
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  Tooltip, CartesianGrid, PieChart, Pie, Cell, BarChart, Bar, Legend
} from 'recharts';

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loanType, setLoanType] = useState('');
  const [riskSegment, setRiskSegment] = useState('');

  const loadData = () => {
    setLoading(true);
    apiClient.getDashboardSummary({
      loan_type: loanType || undefined,
      risk_segment: riskSegment || undefined
    })
      .then(res => setData(res))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [loanType, riskSegment]);

  const COLORS = ['#f43f5e', '#f59e0b', '#3b82f6', '#10b981', '#8b5cf6'];

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mr-3" />
        <span>Calculating dashboard portfolio analytics...</span>
      </div>
    );
  }

  const kpis = data?.kpis;

  // Prepare chart arrays
  const riskChartData = data ? Object.entries(data.risk_distribution).map(([name, value]) => ({ name, value })) : [];
  const loanChartData = data ? Object.entries(data.loan_type_distribution).map(([name, value]) => ({
    name: name.replace('_', ' '),
    amount: Math.round(value / 1000000) // in Millions
  })) : [];
  const complaintChartData = data ? Object.entries(data.complaint_severity_breakdown).map(([name, value]) => ({ name, value })) : [];

  return (
    <div className="space-y-6">

      {/* Top Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Portfolio Filters
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={loanType}
            onChange={(e) => setLoanType(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Loan Products</option>
            <option value="CONSUMER">Consumer Loan</option>
            <option value="BNPL">Buy Now Pay Later (BNPL)</option>
            <option value="CREDIT_CARD">Credit Card</option>
            <option value="PERSONAL">Personal Loan</option>
            <option value="AUTO">Auto Loan</option>
          </select>

          <select
            value={riskSegment}
            onChange={(e) => setRiskSegment(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Risk Segments</option>
            <option value="NPA">NPA (Non-Performing Asset)</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>

          <button
            onClick={loadData}
            title="Refresh Metrics"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Active Accounts"
          value={kpis?.total_accounts.toLocaleString() || 0}
          subtitle={`₹${((kpis?.total_outstanding || 0) / 10000000).toFixed(2)} Cr Total Exposure`}
          icon={<CreditCard className="w-5 h-5 text-blue-400" />}
          variant="default"
        />

        <MetricCard
          title="Delinquent Overdue"
          value={`₹${((kpis?.overdue_outstanding || 0) / 10000000).toFixed(2)} Cr`}
          subtitle={`${kpis?.overdue_accounts.toLocaleString()} Accounts with DPD > 0`}
          change="Urgent Queue"
          isPositive={false}
          icon={<AlertTriangle className="w-5 h-5 text-rose-400" />}
          variant="danger"
        />

        <MetricCard
          title="Recovered Collections"
          value={`₹${((kpis?.payments_collected || 0) / 10000000).toFixed(2)} Cr`}
          subtitle={`Collection Rate: ${kpis?.collection_rate_pct}%`}
          change="+18.4% MoM"
          isPositive={true}
          icon={<DollarSign className="w-5 h-5 text-emerald-400" />}
          variant="success"
        />

        <MetricCard
          title="PTP Fulfillment Rate"
          value={`${kpis?.ptp_kept_pct}%`}
          subtitle={`${kpis?.ptp_rate_pct}% Portfolio Commitments`}
          change="Kept Promises"
          isPositive={true}
          icon={<CalendarCheck className="w-5 h-5 text-indigo-400" />}
          variant="purple"
        />
      </div>

      {/* Secondary Metric Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/40 text-xs">
        <div>
          <span className="text-slate-400 block">Total Principal Portfolio</span>
          <span className="font-mono font-bold text-white text-sm">
            ₹{((kpis?.total_principal || 0) / 10000000).toFixed(2)} Cr
          </span>
        </div>
        <div>
          <span className="text-slate-400 block">High Risk & NPA Accounts</span>
          <span className="font-mono font-bold text-rose-400 text-sm">
            {kpis?.high_risk_accounts.toLocaleString()} ({(kpis ? (kpis.high_risk_accounts / kpis.total_accounts * 100).toFixed(1) : 0)}%)
          </span>
        </div>
        <div>
          <span className="text-slate-400 block">Open Grievances / Complaints</span>
          <span className="font-mono font-bold text-amber-400 text-sm">
            {kpis?.open_complaints.toLocaleString()} of {kpis?.total_complaints.toLocaleString()}
          </span>
        </div>
        <div>
          <span className="text-slate-400 block">Dispute Resolution Rate</span>
          <span className="font-mono font-bold text-emerald-400 text-sm">
            {kpis?.complaint_resolution_rate_pct}% Resolved
          </span>
        </div>
      </div>

      {/* Primary Chart: Recovery Trend Over Time */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              Collections Recovery & Transaction Trend
            </h3>
            <p className="text-xs text-slate-400">
              Daily successful collection amounts (₹) and volume trends across the recovery cycle
            </p>
          </div>
          <button
            onClick={() => onNavigate('work-queue')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 transition-colors"
          >
            <Flame className="w-3.5 h-3.5 text-amber-400" />
            Open Priority Work Queue
          </button>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data?.trends || []}>
              <defs>
                <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `₹${(v/100000).toFixed(0)}L`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                formatter={(value: any) => [`₹${Number(value).toLocaleString()}`, 'Collections']}
              />
              <Area type="monotone" dataKey="collected_amount" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorAmount)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Secondary Charts: Risk Distribution & Loan Types */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Risk Breakdown */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">
              Credit Risk Segmentation
            </h4>
            <p className="text-xs text-slate-400 mb-4">Accounts distributed across portfolio risk tiers</p>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {riskChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Loan Product Outstanding */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">
            Exposure by Loan Product (₹ Millions)
          </h4>
          <p className="text-xs text-slate-400 mb-4">Outstanding balance distribution across products</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={loanChartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#64748b" fontSize={10} tickFormatter={(v) => `₹${v}M`} />
                <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={10} width={80} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                <Bar dataKey="amount" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Grievance Severities */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">
              Grievance Severity Breakdown
            </h4>
            <p className="text-xs text-slate-400 mb-4">Regulatory & Fair Practices complaints</p>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={complaintChartData}
                  cx="50%"
                  cy="50%"
                  outerRadius={75}
                  dataKey="value"
                >
                  {complaintChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

    </div>
  );
};
