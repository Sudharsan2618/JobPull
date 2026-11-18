'use client';
import React from 'react';
import { api, type Job } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Drawer } from '@/components/ui/Drawer';

const LIMIT = 50;
const STATUS = [{ v: 'matched', l: 'Matched' }, { v: 'rejected', l: 'Rejected' }, { v: 'all', l: 'All' }];
const CITIES = [{ v: '', l: 'Both cities' }, { v: 'chennai', l: 'Chennai' }, { v: 'bengaluru', l: 'Bengaluru' }];
const DATES = [{ v: 0, l: 'Any time' }, { v: 1, l: '24 hours' }, { v: 3, l: '3 days' }, { v: 7, l: '7 days' }, { v: 30, l: '30 days' }];
const SOURCES = [{ v: '', l: 'All sources' }, { v: 'naukri', l: 'Naukri' }, { v: 'linkedin', l: 'LinkedIn' }, { v: 'indeed', l: 'Indeed' }];

function fmtDate(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '—' : `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function JobsPage() {
  const [status, setStatus] = React.useState('matched');
  const [city, setCity] = React.useState('');
  const [days, setDays] = React.useState(0);
  const [source, setSource] = React.useState('');

  const [items, setItems] = React.useState<Job[]>([]);
  const [total, setTotal] = React.useState(0);
  const [hasMore, setHasMore] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);

  const [selected, setSelected] = React.useState<Job | null>(null);
  const [open, setOpen] = React.useState(false);
  const [fullDesc, setFullDesc] = React.useState<string | undefined>(undefined);

  const load = React.useCallback((p: number) => {
    setLoading(true);
    api.jobs({ status, city, days, source, page: p, limit: LIMIT })
      .then(res => {
        setItems(prev => (p === 1 ? res.items : [...prev, ...res.items]));
        setTotal(res.total); setHasMore(res.hasMore); setPage(res.page);
      })
      .catch(() => { if (p === 1) { setItems([]); setTotal(0); setHasMore(false); } })
      .finally(() => setLoading(false));
  }, [status, city, days, source]);

  React.useEffect(() => { load(1); }, [load]);

  const openJob = (j: Job) => {
    setSelected(j); setOpen(true); setFullDesc(undefined);
    api.job(j.id).then(f => setFullDesc(f.description || '')).catch(() => setFullDesc(''));
  };

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <PageHeader title="Jobs" subtitle={`${total} ${status === 'matched' ? 'matched' : status} roles · Chennai & Bengaluru`} />

      <div style={{ padding: '20px 28px', display: 'grid', gridTemplateColumns: '220px 1fr', gap: '18px', alignItems: 'start' }}>
        <aside style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '6px 6px 12px', position: 'sticky', top: '14px' }}>
          <FilterGroup label="Status">
            {STATUS.map(s => <Radio key={s.v} name="st" label={s.l} checked={status === s.v} onChange={() => setStatus(s.v)} />)}
          </FilterGroup>
          <FilterGroup label="📍 City">
            {CITIES.map(c => <Radio key={c.v} name="city" label={c.l} checked={city === c.v} onChange={() => setCity(c.v)} />)}
          </FilterGroup>
          <FilterGroup label="Posted within">
            {DATES.map(d => <Radio key={d.v} name="dt" label={d.l} checked={days === d.v} onChange={() => setDays(d.v)} />)}
          </FilterGroup>
          <FilterGroup label="Source">
            {SOURCES.map(s => <Radio key={s.v} name="src" label={s.l} checked={source === s.v} onChange={() => setSource(s.v)} />)}
          </FilterGroup>
        </aside>

        <div>
          <div style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table className="jp-table">
                <thead>
                  <tr><th>Role</th><th>Company</th><th>City</th><th>Exp</th><th>Posted</th><th style={{ textAlign: 'right' }}>Status</th></tr>
                </thead>
                <tbody>
                  {loading && items.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-text-3)' }}><Spinner /> loading…</td></tr>
                  ) : items.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-text-3)' }}>No jobs match these filters.</td></tr>
                  ) : items.map(j => (
                    <tr key={j.id} tabIndex={0} role="button" style={{ cursor: 'pointer' }}
                      onClick={() => openJob(j)}
                      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openJob(j); } }}>
                      <td style={{ verticalAlign: 'top', maxWidth: '340px' }}>
                        <div style={{ fontWeight: 650, lineHeight: 1.35 }}>{j.title}</div>
                        {j.skills && j.skills.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '7px' }}>
                            {j.skills.slice(0, 4).map(s => <Badge key={s} variant="neutral" style={{ fontSize: '11px', padding: '2px 8px' }}>{s}</Badge>)}
                          </div>
                        )}
                        {(j.accepted ? j.relevance?.reason : j.rejectionReason) && (
                          <div style={{ fontSize: '11.5px', marginTop: '7px', color: j.accepted ? 'var(--color-text-2)' : 'var(--color-danger-text)', maxWidth: '340px', lineHeight: 1.4 }}>
                            {j.accepted ? j.relevance?.reason : j.rejectionReason}
                          </div>
                        )}
                      </td>
                      <td style={{ verticalAlign: 'top' }}>
                        <div>{j.company}</div>
                        <div style={{ marginTop: '7px' }}><Badge variant="neutral">{j.ats || j.source}</Badge></div>
                      </td>
                      <td style={{ verticalAlign: 'top', color: 'var(--color-text-2)', maxWidth: '150px', lineHeight: 1.4 }}>{j.location || '—'}</td>
                      <td className="mono" style={{ verticalAlign: 'top', whiteSpace: 'nowrap', color: 'var(--color-text-2)', fontSize: '12.5px' }}>{j.experience || '—'}</td>
                      <td className="mono" style={{ verticalAlign: 'top', whiteSpace: 'nowrap', color: 'var(--color-text-2)', fontSize: '12.5px' }}>{fmtDate(j.createdAt)}</td>
                      <td style={{ verticalAlign: 'top', textAlign: 'right' }}>
                        {j.accepted ? <Badge variant="success">✓ match</Badge> : <Badge variant="neutral">rejected</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {(hasMore || (loading && items.length > 0)) && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '16px' }}>
              <Button variant="secondary" disabled={loading} onClick={() => load(page + 1)}>
                {loading ? <><Spinner size={14} /> loading…</> : `Load more (${items.length} of ${total})`}
              </Button>
            </div>
          )}
        </div>
      </div>

      <Drawer open={open} onClose={() => setOpen(false)}>
        {selected && <JobDetail job={selected} description={fullDesc} onClose={() => setOpen(false)} />}
      </Drawer>
    </div>
  );
}

function JobDetail({ job, description, onClose }: { job: Job; description?: string; onClose: () => void }) {
  const rel = job.relevance || {};
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '18px 20px', borderBottom: '1px solid var(--color-border)' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '16px' }}>{job.title}</div>
          <div style={{ color: 'var(--color-text-2)', fontSize: '13px', marginTop: '3px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            {job.company} <Badge variant="neutral">{job.ats || job.source}</Badge>
          </div>
        </div>
        <button onClick={onClose} aria-label="Close" style={{ marginLeft: 'auto', background: 'none', border: 'none', fontSize: '20px', color: 'var(--color-text-3)', cursor: 'pointer' }}>✕</button>
      </div>
      <div style={{ padding: '18px 20px', overflow: 'auto' }}>
        <div style={{ marginBottom: '14px' }}>
          {job.accepted ? <Badge variant="success">✓ Matched</Badge> : <><Badge variant="neutral">Rejected</Badge> <span style={{ color: 'var(--color-danger-text)', fontSize: '12px', marginLeft: '6px' }}>{job.rejectionReason}</span></>}
        </div>
        <dl style={{ display: 'grid', gridTemplateColumns: '112px 1fr', gap: '7px 12px', fontSize: '13px', margin: '0 0 16px' }}>
          <dt style={{ color: 'var(--color-text-2)' }}>Location</dt><dd style={{ margin: 0 }} className="mono">{job.location || '—'}</dd>
          <dt style={{ color: 'var(--color-text-2)' }}>Experience</dt><dd style={{ margin: 0 }}>{job.experience || '—'}</dd>
          <dt style={{ color: 'var(--color-text-2)' }}>Decision by</dt><dd style={{ margin: 0 }}>{rel.engine || '—'}{rel.seniority ? ` · ${rel.seniority}` : ''}</dd>
          <dt style={{ color: 'var(--color-text-2)' }}>Apply</dt>
          <dd style={{ margin: 0 }}><a href={job.url} target="_blank" rel="noopener" className="mono" style={{ wordBreak: 'break-all', fontSize: '12px' }}>{job.url}</a></dd>
        </dl>
        {rel.reason && (<><SectionLabel>Why</SectionLabel><p style={{ margin: '0 0 14px', fontSize: '13px', lineHeight: 1.55 }}>{rel.reason}</p></>)}
        {job.skills && job.skills.length > 0 && (
          <><SectionLabel>Skills</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px' }}>
              {job.skills.map(s => <Badge key={s} variant="neutral">{s}</Badge>)}
            </div></>
        )}
        <SectionLabel>Description</SectionLabel>
        <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '13px 15px', fontSize: '13px', lineHeight: 1.6, maxHeight: '260px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
          {description === undefined ? <span style={{ color: 'var(--color-text-3)' }}><Spinner size={13} /> loading description…</span> : (description || '(no description stored)')}
        </div>
        <div style={{ marginTop: '16px' }}>
          <a href={job.url} target="_blank" rel="noopener" style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', background: 'var(--color-brand)', color: '#fff', padding: '8px 16px', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600 }}>Open posting ↗</a>
        </div>
      </div>
    </>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-2)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '7px' }}>{children}</div>;
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '10px 10px 4px' }}>
      <h4 style={{ margin: '0 0 8px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-3)' }}>{label}</h4>
      {children}
    </div>
  );
}

function Radio({ name, label, checked, onChange }: { name: string; label: string; checked: boolean; onChange: () => void }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '5px 6px', borderRadius: '7px', cursor: 'pointer', fontSize: '13px' }}>
      <input type="radio" name={name} checked={checked} onChange={onChange} style={{ accentColor: 'var(--color-brand)', width: '15px', height: '15px' }} />
      <span>{label}</span>
    </label>
  );
}
