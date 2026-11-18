'use client';
import React from 'react';
import { api, type Company, type DetectResult } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Modal } from '@/components/ui/Modal';

function fmtDate(iso?: string | null): string {
  if (!iso) return 'never';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? 'never' : `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function CompaniesPage() {
  const [companies, setCompanies] = React.useState<Company[] | null>(null);
  const [adding, setAdding] = React.useState(false);

  const load = React.useCallback(() => {
    api.companies().then(setCompanies).catch(() => setCompanies([]));
  }, []);
  React.useEffect(() => { load(); }, [load]);

  const verify = async (name: string) => { await api.verifyCompany(name); load(); };
  const remove = async (name: string) => {
    if (!confirm(`Remove ${name}?`)) return;
    await api.deleteCompany(name);
    load();
  };

  return (
    <div style={{ maxWidth: '1180px', margin: '0 auto' }}>
      <PageHeader
        title="Companies & Connectors"
        subtitle="Detected once, verified, then monitored — never guessed from the name"
        actions={<Button onClick={() => setAdding(true)}>＋ Add company</Button>}
      />
      <div style={{ padding: '20px 28px' }}>
        <div style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="jp-table">
              <thead>
                <tr><th>Company</th><th>Backend</th><th>Status</th><th>Endpoint</th><th>Cities</th><th>Last pull</th><th></th></tr>
              </thead>
              <tbody>
                {companies == null ? (
                  <tr><td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-text-3)' }}><Spinner /> loading…</td></tr>
                ) : companies.length === 0 ? (
                  <tr><td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: 'var(--color-text-3)' }}>No companies yet — add one to start monitoring.</td></tr>
                ) : companies.map(c => {
                  const ok = c.status === 'verified';
                  return (
                    <tr key={c.name}>
                      <td style={{ fontWeight: 650 }}>{c.name}</td>
                      <td><Badge variant="info">{c.type}</Badge></td>
                      <td>{ok ? <Badge variant="success">✓ verified</Badge> : <Badge variant="warning">⚠ {c.status || 'unverified'}</Badge>}</td>
                      <td className="mono" style={{ fontSize: '12px', maxWidth: '230px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.host || c.token || c.careers_url || ''}</td>
                      <td className="mono" style={{ fontSize: '12px', color: 'var(--color-text-2)' }}>{(c.cities || []).join(', ')}</td>
                      <td style={{ color: 'var(--color-text-2)' }}>{fmtDate(c.lastPull)}</td>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        <Button size="sm" variant="secondary" onClick={() => verify(c.name)} style={{ marginRight: '6px' }}>Verify</Button>
                        <Button size="sm" variant="secondary" onClick={() => remove(c.name)}>✕</Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {adding && <AddCompany onClose={() => setAdding(false)} onAdded={() => { setAdding(false); load(); }} />}
    </div>
  );
}

function AddCompany({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const [step, setStep] = React.useState(0);
  const [name, setName] = React.useState('');
  const [url, setUrl] = React.useState('');
  const [detecting, setDetecting] = React.useState(false);
  const [detected, setDetected] = React.useState<DetectResult | null>(null);
  const [cities, setCities] = React.useState<string[]>(['Chennai', 'Bengaluru']);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const runDetect = async () => {
    if (!url.trim()) return;
    setStep(1); setDetecting(true); setError(null);
    try {
      const d = await api.detectCompany(url.trim(), name.trim());
      setDetected(d);
    } catch {
      setError('Detection failed. Check the URL.');
    } finally {
      setDetecting(false);
    }
  };

  const save = async () => {
    if (!detected) return;
    setSaving(true); setError(null);
    try {
      const doc: Record<string, unknown> = {
        ...detected, name: name.trim() || detected.host || detected.token,
        careers_url: url.trim(), cities, enabled: true,
      };
      delete doc.verify;
      await api.addCompany(doc);
      onAdded();
    } catch {
      setError('Could not save the connector.');
      setSaving(false);
    }
  };

  const toggleCity = (c: string) => setCities(cs => cs.includes(c) ? cs.filter(x => x !== c) : [...cs, c]);
  const v = detected?.verify;

  const footer = step === 0
    ? <Button onClick={runDetect} disabled={!url.trim()}>Detect →</Button>
    : step === 1
      ? <><Button variant="secondary" onClick={() => setStep(0)}>← Back</Button><Button onClick={() => setStep(2)} disabled={!detected?.type}>Looks right →</Button></>
      : <><Button variant="secondary" onClick={() => setStep(1)}>← Back</Button><Button onClick={save} disabled={saving}>{saving ? 'Saving…' : '✓ Add & monitor'}</Button></>;

  return (
    <Modal open onClose={onClose} title="Add company" footer={footer}>
      <div style={{ display: 'flex', gap: '6px', marginBottom: '16px' }}>
        {[0, 1, 2].map(i => <div key={i} style={{ flex: 1, height: '4px', borderRadius: '3px', background: step > i ? 'var(--color-success)' : step === i ? 'var(--color-brand)' : 'var(--color-surface)' }} />)}
      </div>

      {step === 0 && (
        <div>
          <Label>Company name</Label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Capgemini" style={inputStyle} />
          <Label style={{ marginTop: '12px' }}>Careers URL</Label>
          <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://…/careers" className="mono" style={inputStyle} />
          <p style={hintStyle}>We read the page&apos;s real backend — Workday, Greenhouse, Lever, Ashby — instead of guessing.</p>
        </div>
      )}

      {step === 1 && (
        detecting ? <div style={{ textAlign: 'center', padding: '24px' }}><Spinner /> detecting…</div> : error ? <div style={{ color: 'var(--color-danger-text)' }}>{error}</div> : detected && (
          <div>
            <div style={{ fontWeight: 650, marginBottom: '8px' }}>Detected backend</div>
            <div style={{ border: '1px dashed var(--color-border-2)', borderRadius: '11px', padding: '14px', background: 'var(--color-surface)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '9px', padding: '4px 0' }}>🔎 Backend: <Badge variant="info">{detected.type}</Badge></div>
              {detected.host && <div className="mono" style={{ fontSize: '12px', padding: '4px 0' }}>🔗 {detected.host}</div>}
              {detected.token && <div className="mono" style={{ fontSize: '12px', padding: '4px 0' }}>🔗 token {detected.token}</div>}
              <div style={{ padding: '4px 0', fontSize: '13px' }}>{v?.ok ? `✅ live sample OK — ${v.count} jobs` : `⚠ ${v?.error || detected.note || 'needs a manual connector'}`}</div>
            </div>
            {v?.sample && v.sample.length > 0 && (
              <div style={{ border: '1px solid var(--color-border)', borderRadius: '9px', marginTop: '10px', overflow: 'hidden' }}>
                {v.sample.map((s, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', padding: '8px 12px', fontSize: '12.5px', borderBottom: i < v.sample!.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
                    <span>{s.title}</span><span className="mono" style={{ color: 'var(--color-text-3)' }}>{s.location || ''}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      )}

      {step === 2 && (
        <div>
          <div style={{ fontWeight: 650, marginBottom: '10px' }}>Cities (primary filter)</div>
          {['Chennai', 'Bengaluru'].map(c => (
            <label key={c} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '5px 6px', cursor: 'pointer', fontSize: '13px' }}>
              <input type="checkbox" checked={cities.includes(c)} onChange={() => toggleCity(c)} style={{ accentColor: 'var(--color-brand)' }} /> {c}
            </label>
          ))}
          <p style={hintStyle}>Saved to the registry. The daily run will pull {detected?.type} jobs in your cities.</p>
          {error && <div style={{ color: 'var(--color-danger-text)', fontSize: '12.5px', marginTop: '8px' }}>{error}</div>}
        </div>
      )}
    </Modal>
  );
}

function Label({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--color-text-2)', margin: '0 0 6px', ...style }}>{children}</label>;
}

const inputStyle: React.CSSProperties = { width: '100%', height: '38px', border: '1px solid var(--color-border-2)', borderRadius: '9px', background: 'var(--color-bg)', color: 'var(--color-text-1)', padding: '0 12px', fontSize: '13.5px', fontFamily: 'inherit' };
const hintStyle: React.CSSProperties = { fontSize: '12px', color: 'var(--color-text-3)', marginTop: '10px', lineHeight: 1.5 };
