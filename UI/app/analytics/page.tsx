'use client';
import React from 'react';
import { api, type Analytics, type Market } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card } from '@/components/ui/Card';
import { BarList } from '@/components/ui/BarList';
import { Spinner } from '@/components/ui/Spinner';

type Period = 'daily' | 'weekly' | 'monthly';

const SKILL_ORDER = ['skills_concepts', 'frameworks', 'languages', 'tools_platforms', 'databases', 'cloud', 'methodologies'];
const SKILL_LABELS: Record<string, string> = {
  skills_concepts: 'Skills / Concepts', frameworks: 'Frameworks', languages: 'Languages',
  tools_platforms: 'Tools & Platforms', databases: 'Databases', cloud: 'Cloud', methodologies: 'Methodologies',
};

function fmtBucket(b: string, period: Period): string {
  if (period !== 'daily') return b;
  const d = new Date(b);
  return isNaN(d.getTime()) ? b : `${d.getMonth() + 1}/${d.getDate()}`;
}

function PostingsChart({ data, period }: { data: { bucket: string; posted: number; matched: number }[]; period: Period }) {
  if (!data || data.length === 0) {
    return <div style={{ color: 'var(--color-text-3)', fontSize: '13px', padding: '24px 0' }}>No data for this period yet.</div>;
  }
  const max = Math.max(...data.map(d => d.posted), ...data.map(d => d.matched), 1);
  const H = 150;
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: `${H + 8}px` }}>
        {data.map(d => (
          <div key={d.bucket} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: `${H}px`, width: '100%', justifyContent: 'center' }}>
              <div title={`posted ${d.posted}`} style={{ width: '40%', maxWidth: '18px', height: `${Math.round((d.posted / max) * H)}px`, background: 'var(--color-brand-subtle)', border: '1px solid var(--color-brand)', borderBottom: 'none', borderRadius: '4px 4px 0 0', minHeight: '2px' }} />
              <div title={`matched ${d.matched}`} style={{ width: '40%', maxWidth: '18px', height: `${Math.round((d.matched / max) * H)}px`, background: 'var(--color-success)', borderRadius: '4px 4px 0 0', minHeight: '2px' }} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
        {data.map(d => (
          <div key={d.bucket} className="mono" style={{ flex: 1, fontSize: '10px', color: 'var(--color-text-3)', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {fmtBucket(d.bucket, period)}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '16px', marginTop: '14px', fontSize: '12px', color: 'var(--color-text-2)' }}>
        <span><i style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '3px', background: 'var(--color-brand-subtle)', border: '1px solid var(--color-brand)', marginRight: '5px', verticalAlign: '-1px' }} />Posted (new)</span>
        <span><i style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '3px', background: 'var(--color-success)', marginRight: '5px', verticalAlign: '-1px' }} />Matched</span>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [a, setA] = React.useState<Analytics | null>(null);
  const [m, setM] = React.useState<Market | null>(null);
  const [period, setPeriod] = React.useState<Period>('daily');

  React.useEffect(() => {
    api.analytics().then(setA).catch(() => setA(null));
    api.market().then(setM).catch(() => setM(null));
  }, []);

  const series = a ? (a[period] || []) : [];

  return (
    <div style={{ maxWidth: '1180px', margin: '0 auto', paddingBottom: '48px' }}>
      <PageHeader title="Analytics" subtitle="What your matched roles look like, and the skills this market is asking for" />

      <div style={{ padding: '20px 28px 0', display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '16px', alignItems: 'start' }}>
        <Card
          title="Postings vs matches"
          action={
            <div style={{ display: 'flex', gap: '4px' }}>
              {(['daily', 'weekly', 'monthly'] as Period[]).map(p => (
                <button key={p} onClick={() => setPeriod(p)} style={segBtn(period === p)}>{p[0].toUpperCase() + p.slice(1)}</button>
              ))}
            </div>
          }
        >
          {a == null ? <div style={{ padding: '24px 0', textAlign: 'center' }}><Spinner /></div> : <PostingsChart data={series} period={period} />}
        </Card>

        <Card title="Matched by company" subtitle="real employers only" bodyStyle={{ padding: 0 }}>
          <div style={{ maxHeight: '320px', overflow: 'auto' }}>
            <table className="jp-table">
              <tbody>
                {a == null ? (
                  <tr><td style={{ padding: '20px', textAlign: 'center' }}><Spinner /></td></tr>
                ) : a.byCompany.length === 0 ? (
                  <tr><td style={{ padding: '20px', color: 'var(--color-text-3)' }}>No matches yet.</td></tr>
                ) : a.byCompany.map(r => (
                  <tr key={r.company}><td style={{ fontWeight: 600 }}>{r.company}</td><td className="mono" style={{ textAlign: 'right' }}>{r.n}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div style={{ padding: '16px 28px 0', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', alignItems: 'start' }}>
        <Card title="Title categories">
          <BarList items={m ? Object.entries(m.categories).sort((x, y) => y[1] - x[1]) : []} emptyHint="Run LLM analysis to populate." />
        </Card>
        <Card title="Locations">
          <BarList items={m ? Object.entries(m.locations).sort((x, y) => y[1] - x[1]).slice(0, 10) : []} emptyHint="No data yet." />
        </Card>
      </div>

      <div style={{ padding: '16px 28px 0' }}>
        <Card title="What this market wants" subtitle={m ? `share of ${m.denom} analyzed roles` : undefined}>
          <BarList items={m ? m.market : []} denom={m?.denom} emptyHint="Run LLM analysis (Schedules) to populate skills." />
        </Card>
      </div>

      <div style={{ padding: '16px 28px 0' }}>
        <Card title="Skills by category">
          {m == null ? <Spinner /> : (
            SKILL_ORDER.some(b => (m.buckets[b] || []).length) ? SKILL_ORDER.map(b => {
              const items = m.buckets[b] || [];
              if (!items.length) return null;
              return (
                <div key={b} style={{ marginBottom: '14px' }}>
                  <h4 style={{ margin: '0 0 7px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-3)' }}>{SKILL_LABELS[b]}</h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {items.slice(0, 18).map(([skill, n]) => (
                      <span key={skill} style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-full)', padding: '3px 10px', fontSize: '12px' }}>
                        {skill}<b className="mono" style={{ color: 'var(--color-brand)', marginLeft: '5px' }}>{n}</b>
                      </span>
                    ))}
                  </div>
                </div>
              );
            }) : <div style={{ color: 'var(--color-text-3)', fontSize: '13px' }}>Run LLM analysis (Schedules) to populate skills.</div>
          )}
        </Card>
      </div>
    </div>
  );
}

function segBtn(on: boolean): React.CSSProperties {
  return {
    border: `1px solid ${on ? 'transparent' : 'var(--color-border)'}`,
    background: on ? 'var(--color-brand-tint)' : 'var(--color-bg)',
    color: on ? 'var(--color-brand)' : 'var(--color-text-2)',
    height: '28px', padding: '0 11px', borderRadius: '7px', fontSize: '12.5px', fontWeight: 600, cursor: 'pointer',
  };
}
