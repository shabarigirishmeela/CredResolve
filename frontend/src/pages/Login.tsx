import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { DemoUser } from '../types';
import {
  ShieldCheck, Lock, Mail, ArrowRight,
  Sparkles, AlertCircle, Database, X, Info,
  Eye, EyeOff, CheckCircle2, Key, Cpu,
  Layers, Shield
} from 'lucide-react';

// Google SVG icon
const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
    <g fill="none" fillRule="evenodd">
      <path
        d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
        fill="#34A853"
      />
      <path
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"
        fill="#EA4335"
      />
    </g>
  </svg>
);

// Google OAuth info modal
const GoogleInfoModal: React.FC<{ onClose: () => void }> = ({ onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
    <div
      className="relative z-10 w-full max-w-sm rounded-2xl border border-slate-700/60 bg-slate-900 p-5 shadow-2xl"
      onClick={(e) => e.stopPropagation()}
    >
      <button
        onClick={onClose}
        className="absolute right-4 top-4 text-slate-500 hover:text-slate-300 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
          <Info className="w-4 h-4 text-blue-400" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white">Google SSO Setup Guide</h3>
          <p className="text-[11px] text-slate-400">OAuth 2.0 configuration</p>
        </div>
      </div>

      <p className="text-xs text-slate-300 leading-relaxed mb-3">
        Google Single Sign-On is integrated in the CredResolve authentication layer. Configure your Google Cloud OAuth credentials in the environment:
      </p>

      <div className="rounded-xl bg-slate-950 border border-slate-800 p-2.5 font-mono text-[10px] text-slate-400 space-y-1 mb-3">
        <div><span className="text-indigo-400">GOOGLE_CLIENT_ID</span>=your-client-id.apps.googleusercontent.com</div>
        <div><span className="text-indigo-400">GOOGLE_CLIENT_SECRET</span>=your-oauth-client-secret</div>
        <div><span className="text-indigo-400">GOOGLE_DEFAULT_ROLE</span>=agent</div>
      </div>

      <p className="text-[11px] text-slate-400 mb-4">
        Normal email/password login and verified 1-click demo profiles below are operational.
      </p>

      <button
        onClick={onClose}
        className="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-colors"
      >
        Continue with Demo Accounts
      </button>
    </div>
  </div>
);

const DEFAULT_DEMO_USERS: DemoUser[] = [
  {
    email: 'admin@credresolve.com',
    password: 'credresolve123',
    full_name: 'Rajesh Sharma',
    role: 'admin',
    description: 'Full administrative control, configuration, audit and user management'
  },
  {
    email: 'manager@credresolve.com',
    password: 'credresolve123',
    full_name: 'Priya Nair',
    role: 'manager',
    description: 'Operations head, campaign analytics, agent performance oversight'
  },
  {
    email: 'agent@credresolve.com',
    password: 'credresolve123',
    full_name: 'Anil Verma',
    role: 'agent',
    description: 'Senior recovery agent, active queue, borrower contact logs'
  },
  {
    email: 'auditor@credresolve.com',
    password: 'credresolve123',
    full_name: 'Kavita Rao',
    role: 'auditor',
    description: 'Compliance & grievance auditor, Fair Practices Code tracking'
  }
];

export const Login: React.FC = () => {
  const { login, demoLogin, isLoading } = useAuth();
  const [email, setEmail] = useState('admin@credresolve.com');
  const [password, setPassword] = useState('credresolve123');
  const [showPassword, setShowPassword] = useState(false);
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>(DEFAULT_DEMO_USERS);
  const [selectedRole, setSelectedRole] = useState<string>('admin');
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>('Profile pre-loaded. Click "Sign In to Portal" to enter.');
  const [showGoogleInfo, setShowGoogleInfo] = useState(false);

  useEffect(() => {
    apiClient.getDemoUsers()
      .then(res => {
        if (res && res.length > 0) {
          setDemoUsers(res);
        }
      })
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password.');
    }
  };

  const handleSelectDemoProfile = (u: DemoUser) => {
    setEmail(u.email);
    setPassword(u.password);
    setSelectedRole(u.role);
    setError(null);
    setInfoMessage(`Populated ${u.full_name} (${u.role.toUpperCase()}) credentials into form.`);
  };

  const handleQuickSignIn = async (u: DemoUser) => {
    setEmail(u.email);
    setPassword(u.password);
    setSelectedRole(u.role);
    setError(null);
    setInfoMessage(null);
    try {
      await demoLogin(u);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to authenticate demo user.');
    }
  };

  const getRoleTag = (role: string) => {
    switch (role.toLowerCase()) {
      case 'admin':
        return { label: 'Administrator', badge: 'Full Access', color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' };
      case 'manager':
        return { label: 'Operations Head', badge: 'Portfolio Oversight', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20' };
      case 'agent':
        return { label: 'Recovery Agent', badge: 'Active Queue', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
      case 'auditor':
        return { label: 'Compliance Auditor', badge: 'RBI Fair Code', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' };
      default:
        return { label: role, badge: 'Role Access', color: 'text-slate-400 bg-slate-800 border-slate-700' };
    }
  };

  return (
    <>
      {showGoogleInfo && <GoogleInfoModal onClose={() => setShowGoogleInfo(false)} />}

      <div className="min-h-[100dvh] lg:h-screen lg:max-h-screen bg-[#070b13] flex flex-col justify-between overflow-x-hidden lg:overflow-hidden relative text-slate-100">

        {/* Ambient lighting glows */}
        <div className="absolute top-0 left-1/4 w-[500px] h-[350px] bg-indigo-600/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-[450px] h-[300px] bg-blue-600/10 rounded-full blur-[90px] pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none" />

        {/* Top Navbar */}
        <header className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between border-b border-slate-800/60 z-10 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-600 to-cyan-400 flex items-center justify-center text-white font-black text-sm shadow-md shadow-indigo-500/20 ring-1 ring-indigo-500/30">
              CR
            </div>
            <div>
              <span className="font-extrabold text-sm tracking-tight text-white flex items-center gap-1.5">
                CredResolve Intelligence
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  v2.4
                </span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-emerald-400 font-medium bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              RBI Fair Practices Active
            </div>
            <div className="hidden md:flex items-center gap-1.5 text-[11px] text-indigo-300 font-mono bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-full">
              <Database className="w-3 h-3 text-indigo-400" />
              30,000 Verified Accounts
            </div>
          </div>
        </header>

        {/* Main Viewport Container */}
        <main className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 lg:py-4 flex-1 flex flex-col justify-center z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-8 items-center">

            {/* LEFT COLUMN: Enterprise Value & Platform Architecture */}
            <div className="lg:col-span-5 space-y-4">

              <div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-[11px] font-semibold mb-2">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  Enterprise Debt Resolution &amp; Recovery Intelligence
                </div>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight">
                  Deterministic Recovery <br />
                  <span className="bg-gradient-to-r from-indigo-400 via-blue-400 to-cyan-300 bg-clip-text text-transparent">
                    with Regulatory Trust
                  </span>
                </h2>
                <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                  Ingesting 17 relational event streams across 639,185 records to power transparent multi-factor account prioritization, omnichannel contact automation, and strict compliance guardrails.
                </p>
              </div>

              {/* 3 Value Pillars */}
              <div className="space-y-2">
                <div className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm flex items-start gap-3">
                  <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0 mt-0.5">
                    <Cpu className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-200">Intelligent Rule-Based Prioritization</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                      Mathematical 0–100 scoring factoring DPD, exposure, risk segment, PTP commitment history, and contact responsiveness with full point explainability.
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm flex items-start gap-3">
                  <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
                    <Shield className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-200">RBI Fair Practices &amp; Compliance Guardrails</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                      Automatic collection holds on disputed accounts, 08:00 AM – 07:00 PM borrower timezone enforcement, and PII masking.
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm flex items-start gap-3">
                  <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 shrink-0 mt-0.5">
                    <Layers className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-200">Borrower 360° Omnichannel Telemetry</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                      Cross-referenced voice dialer, WhatsApp, SMS, payment reconciliation, and 25,000 GPS field visit dispatches.
                    </p>
                  </div>
                </div>
              </div>

              {/* Data metrics row */}
              <div className="grid grid-cols-3 gap-2 pt-1">
                <div className="px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-center">
                  <div className="text-xs font-bold text-white font-mono">30,000</div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider">Accounts</div>
                </div>
                <div className="px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-center">
                  <div className="text-xs font-bold text-emerald-400 font-mono">98.4%</div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider">Pipeline Health</div>
                </div>
                <div className="px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-center">
                  <div className="text-xs font-bold text-indigo-400 font-mono">17 / 17</div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider">CSV Datasets</div>
                </div>
              </div>

            </div>

            {/* RIGHT COLUMN: LOGIN FORM & ADMIN/DEMO PANEL (BESIDE EACH OTHER ON DESKTOP) */}
            <div className="lg:col-span-7">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">

                {/* SUB-COLUMN 1: THE LOGIN FORM */}
                <div
                  className="rounded-2xl p-5 flex flex-col justify-between shadow-2xl shadow-indigo-950/40 relative overflow-hidden"
                  style={{
                    background: 'rgba(15, 23, 42, 0.88)',
                    backdropFilter: 'blur(16px)',
                    border: '1px solid rgba(51, 65, 85, 0.5)'
                  }}
                >
                  <div className="space-y-3.5">

                    {/* Header */}
                    <div className="border-b border-slate-800 pb-2.5">
                      <h3 className="text-base font-bold text-white tracking-tight flex items-center justify-between">
                        <span>Portal Sign In</span>
                        <span className="text-[10px] font-mono font-normal px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                          Secure JWT
                        </span>
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Enter enterprise credentials or select a role profile
                      </p>
                    </div>

                    {/* Alerts */}
                    {error && (
                      <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/25 text-rose-300 text-[11px] flex items-center gap-2">
                        <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                        <span className="leading-tight">{error}</span>
                      </div>
                    )}

                    {infoMessage && !error && (
                      <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-[11px] flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                        <span className="leading-tight truncate">{infoMessage}</span>
                      </div>
                    )}

                    {/* Google SSO Button */}
                    <button
                      id="google-sso-btn"
                      type="button"
                      onClick={() => setShowGoogleInfo(true)}
                      className="w-full flex items-center justify-center gap-2.5 py-2 px-3 rounded-lg border border-slate-700 bg-slate-900/80 hover:bg-slate-800 hover:border-slate-600 text-xs font-medium text-slate-200 transition-all duration-150 shadow-sm"
                    >
                      <GoogleIcon />
                      <span>Continue with Google SSO</span>
                    </button>

                    {/* Divider */}
                    <div className="flex items-center gap-2.5 my-1">
                      <div className="flex-1 h-px bg-slate-800" />
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">or email sign-in</span>
                      <div className="flex-1 h-px bg-slate-800" />
                    </div>

                    {/* Email/Password Form */}
                    <form onSubmit={handleSubmit} className="space-y-2.5" id="login-form">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-300 uppercase tracking-wider mb-1">
                          Work Email
                        </label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-500">
                            <Mail className="w-3.5 h-3.5" />
                          </div>
                          <input
                            id="login-email"
                            type="email"
                            value={email}
                            onChange={(e) => {
                              setEmail(e.target.value);
                              setInfoMessage(null);
                            }}
                            required
                            placeholder="admin@credresolve.com"
                            className="block w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-transparent transition-all"
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="block text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                            Password
                          </label>
                          <span className="text-[10px] text-slate-500 font-mono">Demo: credresolve123</span>
                        </div>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-500">
                            <Lock className="w-3.5 h-3.5" />
                          </div>
                          <input
                            id="login-password"
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => {
                              setPassword(e.target.value);
                              setInfoMessage(null);
                            }}
                            required
                            placeholder="••••••••••••"
                            className="block w-full pl-8 pr-8 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-transparent transition-all"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            aria-label={showPassword ? 'Hide password' : 'Show password'}
                            className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
                          >
                            {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </div>

                      <button
                        id="login-submit-btn"
                        type="submit"
                        disabled={isLoading}
                        className="w-full mt-2 py-2 px-3 rounded-lg bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                      >
                        <span>{isLoading ? 'Authenticating…' : 'Sign In to Portal'}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </form>

                  </div>

                  {/* Form Footer Note */}
                  <div className="pt-2 mt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3 text-emerald-400" />
                      256-Bit TLS &amp; JWT
                    </span>
                    <span className="font-mono">Port 8000 API</span>
                  </div>
                </div>

                {/* SUB-COLUMN 2: ADMIN / DEMO LOGIN PANEL (BESIDE LOGIN FORM ON DESKTOP) */}
                <div
                  className="rounded-2xl p-4 flex flex-col justify-between shadow-2xl shadow-indigo-950/40 relative overflow-hidden"
                  style={{
                    background: 'rgba(15, 23, 42, 0.88)',
                    backdropFilter: 'blur(16px)',
                    border: '1px solid rgba(51, 65, 85, 0.5)'
                  }}
                >
                  <div className="space-y-2.5">

                    {/* Header */}
                    <div className="border-b border-slate-800 pb-2 flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                            Admin &amp; Demo Profiles
                          </h3>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Click any profile to load credentials into form
                        </p>
                      </div>
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                        4 Verified Roles
                      </span>
                    </div>

                    {/* 4 Demo Role Cards */}
                    <div className="space-y-2">
                      {demoUsers.map((u) => {
                        const isSelected = selectedRole === u.role.toLowerCase() || email === u.email;
                        const roleInfo = getRoleTag(u.role);
                        return (
                          <div
                            key={u.role}
                            className={`p-2 rounded-xl border transition-all text-left ${
                              isSelected
                                ? 'bg-indigo-950/60 border-indigo-500/60 shadow-sm ring-1 ring-indigo-500/30'
                                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-0.5">
                              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                                {u.full_name}
                                {isSelected && (
                                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                )}
                              </span>
                              <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${roleInfo.color}`}>
                                {roleInfo.label}
                              </span>
                            </div>

                            <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1.5">
                              <span className="font-mono text-slate-300 truncate max-w-[150px]">{u.email}</span>
                              <span className="text-slate-500 font-mono text-[9px] flex items-center gap-0.5">
                                <Key className="w-2.5 h-2.5 text-amber-400/80" />
                                {u.password}
                              </span>
                            </div>

                            {/* Action Buttons */}
                            <div className="grid grid-cols-2 gap-1.5">
                              <button
                                type="button"
                                id={`select-profile-${u.role}`}
                                onClick={() => handleSelectDemoProfile(u)}
                                className={`py-1 px-2 rounded-md text-[10px] font-semibold transition-all flex items-center justify-center gap-1 cursor-pointer ${
                                  isSelected
                                    ? 'bg-indigo-600 text-white shadow-sm'
                                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'
                                }`}
                              >
                                <CheckCircle2 className="w-2.5 h-2.5" />
                                <span>{isSelected ? 'Loaded in Form' : 'Use Profile'}</span>
                              </button>

                              <button
                                type="button"
                                id={`instant-signin-${u.role}`}
                                onClick={() => handleQuickSignIn(u)}
                                disabled={isLoading}
                                className="py-1 px-2 rounded-md bg-slate-800/80 hover:bg-emerald-600 hover:text-white text-slate-300 text-[10px] font-semibold transition-all flex items-center justify-center gap-1 border border-slate-700/60 disabled:opacity-50 cursor-pointer"
                              >
                                <span>Instant Sign In</span>
                                <ArrowRight className="w-2.5 h-2.5" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                  </div>

                  {/* Panel Footer */}
                  <div className="pt-2 mt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <Database className="w-3 h-3 text-indigo-400" />
                      SQLite Database Users
                    </span>
                    <span className="text-[10px] font-mono text-emerald-400">
                      bcrypt verified
                    </span>
                  </div>
                </div>

              </div>
            </div>

          </div>
        </main>

        {/* Global Bottom Status Bar */}
        <footer className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/60 text-[11px] text-slate-500 z-10 shrink-0">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              RBI Fair Practices Code (FPC) Guardrails Active
            </span>
            <span className="hidden sm:inline text-slate-700">•</span>
            <span className="hidden sm:inline">Consumer Protection Act 2019 Compliant</span>
          </div>
          <div className="flex items-center gap-3 font-mono text-[10px] text-slate-500">
            <span>Contact Window: 08:00 AM – 07:00 PM IST</span>
            <span>•</span>
            <span className="text-indigo-400">CredResolve Platform v2.4</span>
          </div>
        </footer>

      </div>
    </>
  );
};

export default Login;
