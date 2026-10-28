import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import {
  FileText, Download, BookOpen, Settings,
  ShieldCheck, Database
} from 'lucide-react';

export const ReportsSettings: React.FC = () => {
  const [definitions, setDefinitions] = useState<any>(null);
  const [settingsData, setSettingsData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.getDefinitions(),
      apiClient.getSettings()
    ])
      .then(([dRes, sRes]) => {
        setDefinitions(dRes);
        setSettingsData(sRes);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const exportTypes = [
    { id: 'accounts', name: 'Accounts Portfolio Export', desc: 'Active loan accounts with DPD, risk tiers, and priority scores', filename: 'credresolve_accounts_export.csv' },
    { id: 'queue', name: 'Prioritized Work Queue Export', desc: 'Urgent collection accounts with priority ranking and recommendations', filename: 'credresolve_work_queue_export.csv' },
    { id: 'payments', name: 'Reconciled Payments Ledger', desc: 'Transactions with status, method, reference, and duplicate flags', filename: 'credresolve_payments_export.csv' },
    { id: 'ptp', name: 'Promise to Pay Registry', desc: 'Commitments with promised amounts, dates, and fulfillment status', filename: 'credresolve_ptp_export.csv' },
    { id: 'complaints', name: 'Compliance Grievances Log', desc: 'Dispute audit logs with severity, resolution times, and sources', filename: 'credresolve_complaints_export.csv' }
  ];

  return (
    <div className="space-y-6">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" />
            Reports, CSV Exports & Methodological Definitions
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Download production-ready CSV extracts, review mathematical formula definitions for collection metrics, and inspect active engine settings.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 rounded-lg font-mono">
          <Database className="w-4 h-4" />
          <span>Real Database Streaming Exports</span>
        </div>
      </div>

      {/* CSV Export Cards */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
          <Download className="w-4 h-4 text-emerald-400" />
          Download Filtered CSV Reports
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {exportTypes.map((exp) => (
            <div
              key={exp.id}
              className="p-5 rounded-2xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/40 transition-all flex flex-col justify-between"
            >
              <div>
                <h4 className="text-sm font-bold text-white mb-1">{exp.name}</h4>
                <p className="text-xs text-slate-400 mb-4">{exp.desc}</p>
              </div>

              <a
                href={apiClient.getExportUrl(exp.id)}
                download={exp.filename}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-indigo-400 border border-slate-700 text-xs font-semibold transition-all shadow-sm group"
              >
                <Download className="w-3.5 h-3.5 group-hover:-translate-y-0.5 transition-transform" />
                <span>Export CSV</span>
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* Methodological Definitions & Formulas */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md space-y-6">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-indigo-400" />
            Financial Metric Definitions & Cleaning Decisions
          </h3>
          <p className="text-xs text-slate-400">
            Documented methodologies, formula references, and data-cleaning rules applied to the 30k collections dataset.
          </p>
        </div>

        {/* Financial KPIs */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Core Recovery Metrics
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {definitions?.kpi_metrics?.map((m: any, idx: number) => (
              <div key={idx} className="p-4 rounded-xl border border-slate-800 bg-slate-800/30 space-y-1.5">
                <div className="font-semibold text-white">{m.metric}</div>
                <div className="text-slate-400">{m.definition}</div>
                <div className="pt-1 text-[11px] font-mono text-indigo-400 bg-black/20 p-2 rounded border border-slate-800">
                  Formula: {m.formula}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Prioritization Weights */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Intelligent Recommendation Engine Weights
          </h4>
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/80 text-slate-400 uppercase text-[11px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Priority Factor</th>
                  <th className="py-2.5 px-4 font-semibold">Weight</th>
                  <th className="py-2.5 px-4 font-semibold">Evaluation Rules & Score Scaling</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {definitions?.prioritization_engine_weights?.map((w: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-4 font-semibold text-slate-200">{w.factor}</td>
                    <td className="py-2.5 px-4 font-mono font-bold text-indigo-400">{w.weight}</td>
                    <td className="py-2.5 px-4 font-mono text-slate-400 text-[11px]">{w.logic}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Compliance Guardrails */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Compliance Guardrails & Fair Collections Enforcement
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            {definitions?.compliance_guardrails?.map((g: any, idx: number) => (
              <div key={idx} className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 space-y-1.5">
                <div className="font-semibold text-emerald-300">{g.guardrail}</div>
                <div className="text-[10px] text-emerald-400 font-mono">{g.standard}</div>
                <div className="text-slate-300 leading-relaxed text-[11px]">{g.enforcement}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Data Cleaning Decisions */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Repeatable Data-Cleaning Decisions
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {definitions?.data_cleaning_decisions?.map((c: any, idx: number) => (
              <div key={idx} className="p-4 rounded-xl border border-slate-800 bg-slate-800/40 space-y-1">
                <div className="font-mono font-bold text-indigo-400">{c.dataset}</div>
                <div className="text-rose-400/90 text-[11px]">Identified: {c.issue}</div>
                <div className="text-slate-300 text-[11px]">Rule: {c.cleaning_rule}</div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Engine Settings */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Settings className="w-4 h-4 text-indigo-400" />
          Active Platform Configuration
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
            <span className="text-slate-500 block text-[10px]">PLATFORM VERSION</span>
            <span className="text-white font-bold">{settingsData?.version || '2.4.0-enterprise'}</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
            <span className="text-slate-500 block text-[10px]">DATABASE ENGINE</span>
            <span className="text-emerald-400 font-bold">SQLite 3 / Indexed</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
            <span className="text-slate-500 block text-[10px]">PERMISSIBLE HOURS</span>
            <span className="text-amber-400 font-bold">08:00 - 19:00 Local</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
            <span className="text-slate-500 block text-[10px]">MAX DAILY ATTEMPTS</span>
            <span className="text-blue-400 font-bold">3 Attempts / Day</span>
          </div>
        </div>
      </div>

    </div>
  );
};
