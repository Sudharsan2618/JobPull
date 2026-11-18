'use client';
import React from 'react';
import Link from 'next/link';
import { api, type Analytics, type Job } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatTile } from '@/components/ui/StatTile';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

function fmtDate(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '—' : `${d.getMonth() + 1}/${d.getDate()}`;
}

function srcCaption(bySource: Record<string, number>): string {
  return Object.entries(bySource).slice(0, 3).map(([k, v]) => `${k} ${v}`).join(' · ');
}

export default function OverviewPage() {
  const [a, setA] = React.useState<Analytics | null>(null);
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  const [offline, setOffline] = React.useState(false);

  React.useEffect(() => {
    api.analytics().then(d => { setA(d); setOffline(false); }).catch(() => setOffline(true));
    api.jobs({ status: 'matched', limit: 10 }).then(p => setJobs(p.items)).catch(() => setJobs([]));
  }, []);

  return (
    <div style={{ maxWidth: '1180px', margin: '0 auto', paddingBottom: '48px' }}>
      <PageHeader title="Overview" subtitle="Chennai & Bengaluru · proactive monitoring across job boards and career pages" />

      <div style={{ padding: '20px 28px 0' }}>
        {offline && (
          <div style={{
            background: 'var(--color-danger-bg)', color: 'var(--color-danger-text)',
            border: '1px solid var(--color-danger-border)', borderRadius: 'var(--radius-md)',
            padding: '12px 15px', fontSize: '13px', marginBottom: '18px',
          }}>
            Backend not reachable on <span className="mono">/api</span>. Start it with <span className="mono">uvicorn app.server:app --app-dir BE --port 8000</span>.
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <StatTile label="Matched · today" value={a ? a.today.matched : <Spinner />} caption={a ? `${a.today.posted} new postings` : ''} accent />
          <StatTile label="Matched · total" value={a ? a.accepted : <Spinner />} caption="across all sources" />
          <StatTile label="Tracked" value={a ? a.accepted + a.rejected : <Spinner />} caption={a ? `${a.analyzed} analyzed` : ''} />
          <StatTile label="Sources" value={a ? Object.keys(a.bySource).length : <Spinner />} caption={a ? srcCaption(a.bySource) : ''} />
        </div>

        <Card
          title="Matched recently"
          action={<Link href="/jobs" style={{ fontSize: '13px', fontWeight: 600 }}>Open Jobs →</Link>}
          bodyStyle={{ padding: 0 }}
        >
          <div style={{ overflowX: 'auto' }}>
            <table className="jp-table">
              <thead>
                <tr><th>Role</th><th>Company</th><th>Source</th><th>City</th><th>Why matched</th><th>Seen</th></tr>
              </thead>
              <tbody>
                {jobs == null ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '28px', color: 'var(--color-text-3)' }}><Spinner /> loading…</td></tr>
                ) : jobs.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '28px', color: 'var(--color-text-3)' }}>No matches yet — run a stage from Schedules.</td></tr>
                ) : jobs.map(j => (
                  <tr key={j.id}>
                    <td style={{ fontWeight: 650 }}>{j.title}</td>
                    <td>{j.company}</td>
                    <td><Badge variant="neutral">{j.ats || j.source}</Badge></td>
                    <td className="mono" style={{ fontSize: '12px', color: 'var(--color-text-2)' }}>{(j.location || '').split(',')[0] || '—'}</td>
                    <td style={{ fontSize: '12px', color: 'var(--color-text-2)', maxWidth: '280px' }}>{j.relevance?.reason || '—'}</td>
                    <td className="mono" style={{ fontSize: '12px', color: 'var(--color-text-3)' }}>{fmtDate(j.lastSeenAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
