import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { BorrowerItem } from '../types';
import {
  Users, Search, MapPin, Eye, ChevronLeft,
  ChevronRight, RefreshCw, Shield
} from 'lucide-react';

interface BorrowersProps {
  onOpenBorrower: (borrowerId: string) => void;
}

export const Borrowers: React.FC<BorrowersProps> = ({ onOpenBorrower }) => {
  const [items, setItems] = useState<BorrowerItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const loadBorrowers = () => {
    setLoading(true);
    apiClient.getBorrowers({
      search: search || undefined,
      page,
      page_size: pageSize
    })
      .then(res => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadBorrowers();
  }, [page]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadBorrowers();
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-5">

      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            Borrower Directory & 360° Profiles
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Complete registry of borrowers, active loan commitments, masked PII compliance, and consolidated exposure.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg font-medium">
          <Shield className="w-4 h-4" />
          <span>PII Masking Active: GDPR & RBI Compliant</span>
        </div>
      </div>

      {/* Search & Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <form onSubmit={handleSearch} className="flex items-center gap-2 max-w-md w-full">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by Name, Borrower ID, City or Phone..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shrink-0"
          >
            Search
          </button>
        </form>

        <button
          onClick={loadBorrowers}
          title="Refresh List"
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
        </button>
      </div>

      {/* Borrowers Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/70 text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-3 px-4 font-semibold">Borrower Profile</th>
                <th className="py-3 px-4 font-semibold">Contact (Protected)</th>
                <th className="py-3 px-4 font-semibold">Location</th>
                <th className="py-3 px-4 font-semibold">Active Accounts</th>
                <th className="py-3 px-4 font-semibold">Total Outstanding</th>
                <th className="py-3 px-4 font-semibold">Max Delinquency</th>
                <th className="py-3 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Fetching borrower directory...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No borrower records matched your query.
                  </td>
                </tr>
              ) : (
                items.map((b) => (
                  <tr key={b.borrower_id} className="hover:bg-slate-800/40 transition-colors">

                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{b.name}</div>
                      <div className="font-mono text-[11px] text-slate-400">{b.borrower_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono text-slate-300">{b.phone_masked}</div>
                      <div className="text-[11px] text-slate-500 truncate max-w-[160px]">{b.email_masked}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1 text-slate-300">
                        <MapPin className="w-3.5 h-3.5 text-slate-500" />
                        <span>{b.city}, {b.state}</span>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-slate-200 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        {b.account_count} {b.account_count === 1 ? 'Loan' : 'Loans'}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-amber-400">
                        ₹{b.total_outstanding.toLocaleString()}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${
                        b.max_dpd >= 90 ? 'bg-rose-500/20 text-rose-300' :
                        b.max_dpd > 0 ? 'bg-amber-500/20 text-amber-300' :
                        'bg-emerald-500/20 text-emerald-300'
                      }`}>
                        {b.max_dpd} DPD
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onOpenBorrower(b.borrower_id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5 text-indigo-400" />
                        View 360°
                      </button>
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
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} borrowers
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
