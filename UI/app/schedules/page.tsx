'use client';
import React from 'react';
import { api, type Run } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';

const STAGES = [
  { id: 'boards' as const, label: '▶ Job boards', tag: 'Stage 1 · Reactive', desc: 'LinkedIn · Indeed · Naukri — search your titles × cities, then title rejection' },
  { id: 'career' as const, label: '▶ Career pages', tag: 'Stage 2 · Proactive', desc: 'Workday · Greenhouse — location-primary + date window + LLM relevance' },
  { id: 'analyze' as const, label: '▶ LLM analysis', tag: 'Stage 3 · Enrich', desc: 'Gemini extracts skills & experience on new matches — powers Analytics' },
];

function fmtDateTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '—' : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function SchedulesPage() {
  const [runs, setRuns] = React.useState<Run[] | null>(null);
  const [nextRun, setNextRun] = React.useState<string | null>(null);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<string | null>(null);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = React.useCallback(() => {
    api.runs(25).then(rs => {
      setRuns(rs);
      const running = rs.some(r => (r.status || 'done') === 'running');
      if (timer.current) { clearTimeout(timer.current); timer.current = null; }
      if (running) timer.current = setTimeout(load, 4000);
    }).catch(() => setRuns([]));
  }, []);

  React.useEffect(() => {
    load();
    api.health().then(h => setNextRun(h.schedule?.[0]?.next_run || null)).catch(() => {});
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [load]);

  const runStage = async (id: 'boards' | 'career' | 'analyze') => {
    setBusy(id); setMsg(null);
    try {
      const r = await api.runStage(id);
      if (r.started === false) { setMsg(`⚠ ${r.error || 'could not start'}`); }
      else { setMsg(`Started ${id} — running in the background. This table refreshes automatically.`); load(); }
    } catch {
      setMsg('⚠ could not start');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div style={{ maxWidth: '1180px', margin: '0 auto' }}>
      <PageHeader title="Schedules & Runs" subtitle={nextRun ? `Next daily run: ${fmtDateTime(nextRun)} (in-app scheduler, IST)` : 'Run each stage; review run history'} />

      <div style={{ padding: '20px 28px 0' }}>
        <Card title="Run a stage" subtitle="stage by stage">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {STAGES.map((s, i) => (
              <div key={s.id} style={{ display: 'flex', gap: '14px', alignItems: 'center', padding: '12px 0', borderBottom: i < STAGES.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
                <Button variant="secondary" disabled={busy === s.id} onClick={() => runStage(s.id)} style={{ minWidth: '150px' }}>
                  {busy === s.id ? <><Spinner size={13} /> starting…</> : s.label}
                </Button>
                <div>
                  <b style={{ fontSize: '13px' }}>{s.tag}</b>
                  <div style={{ color: 'var(--color-text-2)', fontSize: '12.5px' }}>{s.desc}</div>
                </div>
              </div>
            ))}
            {msg && <div style={{ marginTop: '12px', fontSize: '12.5px', color: msg.startsWith('⚠') ? 'var(--color-danger-text)' : 'var(--color-text-2)' }}>{msg}</div>}
          </div>
        </Card>
      </div>

      <div style={{ padding: '16px 28px 32px' }}>
        <Card title="Run history" bodyStyle={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="jp-table">
              <thead>
                <tr><th>Started</th><th>Scope</th><th>Discovered</th><th>New</th><th>Matched</th><th>Status</th></tr>
              </thead>
              <tbody>
                {runs == null ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '28px', color: 'var(--color-text-3)' }}><Spinner /> loading…</td></tr>
                ) : runs.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '28px', color: 'var(--color-text-3)' }}>No runs yet — run a stage above.</td></tr>
                ) : runs.map(r => {
                  const st = r.status || 'done';
                  return (
                    <tr key={r._id}>
                      <td className="mono">{fmtDateTime(r.startedAt)}</td>
                      <td>{(r.scope || []).join(', ') || '—'}</td>
                      <td className="mono">{r.discovered}</td>
                      <td className="mono">+{r.new}</td>
                      <td className="mono" style={{ color: 'var(--color-success-text)', fontWeight: 600 }}>{r.matched}</td>
                      <td>
                        {st === 'running' ? <Badge variant="warning"><Spinner size={11} /> running</Badge>
                          : (r.errors && r.errors.length) ? <Badge variant="warning">⚠ errors</Badge>
                            : <Badge variant="success">✓ done</Badge>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
