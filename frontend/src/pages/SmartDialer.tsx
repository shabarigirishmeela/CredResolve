import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// Use the existing configured API instance with JWT
const api = axios.create({ baseURL: '/api/v1' });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('credresolve_token');
  if (token && config.headers) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Types ────────────────────────────────────────────────────────────────────

interface Session {
  session_id: string;
  mode: string;
  state: string;
  campaign_id?: string;
  total_initiated: number;
  total_answered: number;
  total_completed: number;
  total_failed: number;
  is_running: boolean;
  agent_states?: Record<string, number>;
  call_states?: Record<string, number>;
}

interface ProviderHealth {
  provider: string;
  healthy: boolean;
  failure_rate: number;
  circuit_state: string;
  consecutive_failures: number;
}

interface PacingData {
  pacing: { proposed_dials: number; explanation: string };
  safety: { verdict: string; approved_dials: number; reason: string };
  rolling_answer_rate: number;
  rolling_avg_talk_sec: number;
}

interface SimResult {
  scenario: string;
  description: string;
  summary: {
    total_initiated: number;
    total_answered: number;
    total_completed: number;
    total_failed: number;
    answer_rate_pct: number;
    peak_utilization_pct: number;
    avg_utilization_pct: number;
    safety_reductions: number;
    safety_rejections: number;
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const VERDICT_COLOR: Record<string, string> = {
  APPROVED: '#22c55e',
  REDUCED:  '#f59e0b',
  REJECTED: '#ef4444',
  FALLBACK: '#a78bfa',
};

const STATE_COLOR: Record<string, string> = {
  CLOSED:    '#22c55e',
  HALF_OPEN: '#f59e0b',
  OPEN:      '#ef4444',
};

const badge = (label: string, color: string) => (
  <span style={{
    padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700,
    background: color + '22', color, border: `1px solid ${color}66`,
  }}>{label}</span>
);

// ── Main Component ────────────────────────────────────────────────────────────

export const SmartDialer: React.FC = () => {
  const [sessions, setSessions]             = useState<Session[]>([]);
  const [activeId, setActiveId]             = useState<string | null>(null);
  const [activeSession, setActiveSession]   = useState<Session | null>(null);
  const [providers, setProviders]           = useState<ProviderHealth[]>([]);
  const [pacing, setPacing]                 = useState<PacingData | null>(null);
  const [mode, setMode]                     = useState<'PROGRESSIVE' | 'PREDICTIVE'>('PREDICTIVE');
  const [simScenario, setSimScenario]       = useState<'A' | 'B' | 'C' | 'D'>('B');
  const [simResult, setSimResult]           = useState<SimResult | null>(null);
  const [simRunning, setSimRunning]         = useState(false);
  const [error, setError]                   = useState<string | null>(null);
  const [agentInput, setAgentInput]         = useState('');
  const [creating, setCreating]             = useState(false);

  // ── Data fetching ──────────────────────────────────────────────────────────

  const fetchSessions = useCallback(async () => {
    try {
      const r = await api.get('/dialer/sessions');
      setSessions(r.data.items || []);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load sessions');
    }
  }, []);

  const fetchProviders = useCallback(async () => {
    try {
      const r = await api.get('/dialer/providers/health');
      setProviders(r.data.providers || []);
    } catch { /* non-fatal */ }
  }, []);

  const fetchActive = useCallback(async () => {
    if (!activeId) return;
    try {
      const [sRes, pRes] = await Promise.all([
        api.get(`/dialer/sessions/${activeId}`),
        api.get(`/dialer/sessions/${activeId}/pacing`).catch(() => null),
      ]);
      setActiveSession(sRes.data);
      if (pRes) setPacing(pRes.data);
    } catch { /* non-fatal */ }
  }, [activeId]);

  useEffect(() => {
    fetchSessions();
    fetchProviders();
  }, [fetchSessions, fetchProviders]);

  useEffect(() => {
    fetchActive();
    const t = setInterval(fetchActive, 3000);
    return () => clearInterval(t);
  }, [fetchActive]);

  // ── Actions ────────────────────────────────────────────────────────────────

  const createSession = async () => {
    setCreating(true);
    try {
      const r = await api.post('/dialer/sessions', { mode, max_dial_rate: 1.0 });
      setActiveId(r.data.session_id);
      await fetchSessions();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Create failed');
    } finally { setCreating(false); }
  };

  const startSession = async (id: string) => {
    try {
      await api.post(`/dialer/sessions/${id}/start`);
      await fetchSessions();
      fetchActive();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Start failed'); }
  };

  const stopSession = async (id: string) => {
    try {
      await api.post(`/dialer/sessions/${id}/stop`);
      await fetchSessions();
      fetchActive();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Stop failed'); }
  };

  const addAgents = async () => {
    if (!activeId || !agentInput.trim()) return;
    const ids = agentInput.split(',').map(s => s.trim()).filter(Boolean);
    try {
      const r = await api.post(`/dialer/sessions/${activeId}/agents`, { agent_ids: ids });
      const { added, skipped } = r.data;
      setAgentInput('');
      fetchActive();
      if (skipped > 0) {
        setError(`${added} agent(s) added, ${skipped} skipped (already in session)`);
        setTimeout(() => setError(null), 3000);
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const status = e?.response?.status;
      if (status === 401) {
        setError('Authentication required. Please log in first.');
      } else if (status === 404) {
        setError('Session not found. Please select a valid session.');
      } else {
        setError(detail || `Add agents failed (status ${status || 'unknown'})`);
      }
    }
  };

  const runSimulation = async () => {
    setSimRunning(true);
    setSimResult(null);
    try {
      const r = await api.post('/dialer/simulate', {
        scenario: simScenario, num_agents: 10, num_borrowers: 100,
        duration_ticks: 20, mode,
      });
      setSimResult(r.data);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Simulation failed'); }
    finally { setSimRunning(false); }
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  const s = activeSession;

  return (
    <div style={{ color: '#e2e8f0', fontFamily: 'Inter, sans-serif', padding: '0 0 40px 0' }}>

      {error && (
        <div style={{ background: '#ef444420', border: '1px solid #ef4444', borderRadius: 8,
          padding: '10px 16px', marginBottom: 16, fontSize: 13, color: '#fca5a5' }}>
          ⚠ {error}
          <button onClick={() => setError(null)} style={{ float: 'right', background: 'none',
            border: 'none', color: '#fca5a5', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* ── Provider Health Bar ── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {providers.length === 0 && (
          <span style={{ fontSize: 13, color: '#64748b' }}>
            No provider health data — start a session first
          </span>
        )}
        {providers.map(p => (
          <div key={p.provider} style={{
            background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10,
            padding: '12px 20px', minWidth: 180,
          }}>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{p.provider}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {badge(p.circuit_state, STATE_COLOR[p.circuit_state] || '#94a3b8')}
              <span style={{ fontSize: 12, color: '#94a3b8' }}>
                Fail: {(p.failure_rate * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
        <button onClick={fetchProviders} style={{
          background: 'none', border: '1px solid #334155', borderRadius: 8,
          color: '#94a3b8', padding: '8px 14px', cursor: 'pointer', fontSize: 12,
        }}>↺ Refresh</button>
      </div>

      {/* ── Session Controls ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>

        {/* Create */}
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#f8fafc' }}>
            New Dialing Session
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: '#94a3b8' }}>Mode:</label>
            {(['PROGRESSIVE', 'PREDICTIVE'] as const).map(m => (
              <button key={m} onClick={() => setMode(m)} style={{
                padding: '4px 12px', borderRadius: 6, border: '1px solid',
                borderColor: mode === m ? '#6366f1' : '#334155',
                background: mode === m ? '#6366f120' : 'transparent',
                color: mode === m ? '#a5b4fc' : '#64748b',
                cursor: 'pointer', fontSize: 12, fontWeight: mode === m ? 700 : 400,
              }}>{m}</button>
            ))}
          </div>
          <button onClick={createSession} disabled={creating} style={{
            padding: '8px 20px', borderRadius: 8, border: 'none',
            background: creating ? '#334155' : '#6366f1', color: '#fff',
            cursor: creating ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: 13,
          }}>{creating ? 'Creating…' : '+ Create Session'}</button>
        </div>

        {/* Session list */}
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#f8fafc' }}>
            Sessions
          </div>
          <div style={{ maxHeight: 130, overflowY: 'auto' }}>
            {sessions.length === 0 && (
              <div style={{ fontSize: 12, color: '#475569' }}>No sessions yet</div>
            )}
            {sessions.map(sess => (
              <div key={sess.session_id} onClick={() => setActiveId(sess.session_id)}
                style={{
                  padding: '8px 10px', borderRadius: 8, marginBottom: 6, cursor: 'pointer',
                  background: activeId === sess.session_id ? '#1e293b' : 'transparent',
                  border: `1px solid ${activeId === sess.session_id ? '#334155' : 'transparent'}`,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                <div>
                  <span style={{ fontSize: 12, color: '#f1f5f9', fontFamily: 'monospace' }}>
                    {sess.session_id.slice(0, 14)}…
                  </span>
                  <span style={{ fontSize: 11, color: '#64748b', marginLeft: 8 }}>{sess.mode}</span>
                </div>
                {badge(sess.state, sess.state === 'RUNNING' ? '#22c55e' : '#64748b')}
              </div>
            ))}
          </div>
          <button onClick={fetchSessions} style={{
            marginTop: 8, background: 'none', border: '1px solid #1e293b',
            borderRadius: 6, color: '#64748b', padding: '4px 10px',
            cursor: 'pointer', fontSize: 11,
          }}>↺</button>
        </div>
      </div>

      {/* ── Active Session Detail ── */}
      {s && (
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12,
          padding: 20, marginBottom: 20 }}>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
                {s.session_id.slice(0, 20)}… — {s.mode}
              </div>
              <div style={{ fontSize: 12, color: '#64748b' }}>
                {badge(s.state, s.state === 'RUNNING' ? '#22c55e' : '#94a3b8')}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {s.state !== 'RUNNING' ? (
                <button onClick={() => startSession(s.session_id)} style={{
                  padding: '8px 18px', borderRadius: 8, border: 'none',
                  background: '#22c55e', color: '#fff', cursor: 'pointer', fontWeight: 600,
                }}>▶ Start</button>
              ) : (
                <button onClick={() => stopSession(s.session_id)} style={{
                  padding: '8px 18px', borderRadius: 8, border: 'none',
                  background: '#ef4444', color: '#fff', cursor: 'pointer', fontWeight: 600,
                }}>■ Stop</button>
              )}
            </div>
          </div>

          {/* Stats grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'Initiated',  value: s.total_initiated, color: '#6366f1' },
              { label: 'Answered',   value: s.total_answered,  color: '#22c55e' },
              { label: 'Completed',  value: s.total_completed, color: '#0ea5e9' },
              { label: 'Failed',     value: s.total_failed,    color: '#ef4444' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                background: '#070b13', borderRadius: 10, padding: '14px 16px',
                borderLeft: `3px solid ${color}`,
              }}>
                <div style={{ fontSize: 22, fontWeight: 800, color }}>{value}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Agent states */}
          {s.agent_states && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>Agent States</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {Object.entries(s.agent_states).map(([state, count]) => (
                  <span key={state} style={{
                    fontSize: 12, padding: '4px 10px', borderRadius: 6,
                    background: '#1e293b', color: '#94a3b8',
                  }}>{state}: <strong style={{ color: '#e2e8f0' }}>{count}</strong></span>
                ))}
              </div>
            </div>
          )}

          {/* Add agents */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 16 }}>
            <input
              value={agentInput}
              onChange={e => setAgentInput(e.target.value)}
              placeholder="agent-1, agent-2, agent-3"
              style={{
                flex: 1, background: '#070b13', border: '1px solid #334155',
                borderRadius: 8, padding: '8px 12px', color: '#e2e8f0',
                fontSize: 13, outline: 'none',
              }}
            />
            <button onClick={addAgents} style={{
              padding: '8px 16px', borderRadius: 8, border: 'none',
              background: '#0ea5e9', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13,
            }}>Add Agents</button>
          </div>

          {/* Pacing / Safety */}
          {pacing && (
            <div style={{ background: '#070b13', borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 10 }}>
                Pacing & Safety
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 10 }}>
                <div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>Proposed Dials</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: '#a5b4fc' }}>
                    {pacing.pacing.proposed_dials}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>Approved Dials</div>
                  <div style={{ fontSize: 22, fontWeight: 800,
                    color: VERDICT_COLOR[pacing.safety.verdict] || '#e2e8f0' }}>
                    {pacing.safety.approved_dials}
                    <span style={{ fontSize: 12, marginLeft: 6 }}>
                      {badge(pacing.safety.verdict, VERDICT_COLOR[pacing.safety.verdict] || '#94a3b8')}
                    </span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>Rolling Answer Rate</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#22c55e' }}>
                    {(pacing.rolling_answer_rate).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>Avg Talk Time</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b' }}>
                    {pacing.rolling_avg_talk_sec.toFixed(0)}s
                  </div>
                </div>
              </div>
              <div style={{ fontSize: 11, color: '#475569', marginBottom: 4 }}>Pacing logic:</div>
              <div style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace',
                background: '#0f172a', borderRadius: 6, padding: '8px 12px', wordBreak: 'break-word' }}>
                {pacing.pacing.explanation}
              </div>
              <div style={{ fontSize: 11, color: '#475569', marginTop: 8, marginBottom: 4 }}>Safety reason:</div>
              <div style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace',
                background: '#0f172a', borderRadius: 6, padding: '8px 12px' }}>
                {pacing.safety.reason}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Simulation ── */}
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', marginBottom: 14 }}>
          Simulation (No Real Calls)
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 14 }}>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>Scenario:</span>
          {(['A', 'B', 'C', 'D'] as const).map(sc => (
            <button key={sc} onClick={() => setSimScenario(sc)} style={{
              padding: '4px 12px', borderRadius: 6, border: '1px solid',
              borderColor: simScenario === sc ? '#6366f1' : '#334155',
              background: simScenario === sc ? '#6366f120' : 'transparent',
              color: simScenario === sc ? '#a5b4fc' : '#64748b',
              cursor: 'pointer', fontSize: 12, fontWeight: simScenario === sc ? 700 : 400,
            }}>
              {sc} {sc === 'A' ? '(20%)' : sc === 'B' ? '(50%)' : sc === 'C' ? '(70%)' : '(dyn)'}
            </button>
          ))}
          <button onClick={runSimulation} disabled={simRunning} style={{
            marginLeft: 'auto', padding: '8px 20px', borderRadius: 8, border: 'none',
            background: simRunning ? '#334155' : '#6366f1', color: '#fff',
            cursor: simRunning ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: 13,
          }}>{simRunning ? 'Running…' : '▶ Run'}</button>
        </div>

        {simResult && (
          <div>
            <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 10 }}>
              Scenario {simResult.scenario} — {simResult.description}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 12 }}>
              {[
                { label: 'Initiated',      value: simResult.summary.total_initiated },
                { label: 'Answered',       value: simResult.summary.total_answered },
                { label: 'Completed',      value: simResult.summary.total_completed },
                { label: 'Failed',         value: simResult.summary.total_failed },
                { label: 'Answer Rate',    value: simResult.summary.answer_rate_pct + '%' },
                { label: 'Peak Util.',     value: simResult.summary.peak_utilization_pct + '%' },
                { label: 'Safety Reduced', value: simResult.summary.safety_reductions },
                { label: 'Safety Rejected',value: simResult.summary.safety_rejections },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  background: '#070b13', borderRadius: 8, padding: '12px 14px',
                }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#a5b4fc' }}>{value}</div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>{label}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SmartDialer;
