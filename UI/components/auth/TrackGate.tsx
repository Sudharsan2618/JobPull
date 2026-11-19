'use client';
import React from 'react';
import { api, type Me } from '@/lib/api';
import { phCapture, phSetPerson } from '@/lib/analytics';
import { Spinner } from '@/components/ui/Spinner';

const TrackContext = React.createContext<string | null>(null);
export const useTrack = () => React.useContext(TrackContext);

export const TRACK_LABEL: Record<string, string> = { genai: 'AI Engineer', fresher: 'IT Fresher' };

const TRACKS = [
  {
    id: 'genai',
    title: 'AI / GenAI Engineer',
    desc: 'Gen AI, AI/ML, Python, LLM & NLP roles at associate–mid level.',
    icon: <path d="M20 4l2.2 7.8L30 14l-7.8 2.2L20 24l-2.2-7.8L10 14l7.8-2.2z" />,
  },
  {
    id: 'fresher',
    title: 'IT Fresher',
    desc: 'Fresher, intern, trainee & junior roles across all of IT — dev, data, QA, support, HR.',
    icon: <path d="M20 6l14 7-14 7L6 13zM12 16v7c0 2.2 3.6 4 8 4s8-1.8 8-4v-7" />,
  },
];

export function TrackGate({ children }: { children: React.ReactNode }) {
  const [me, setMe] = React.useState<Me | null | undefined>(undefined);

  React.useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null));
  }, []);

  // Keep the person's `track` property in sync so dashboards can break down by it.
  React.useEffect(() => {
    if (me && me.track) phSetPerson({ track: me.track });
  }, [me]);

  if (me === undefined) {
    return <div style={{ height: '100vh', display: 'grid', placeItems: 'center', background: 'var(--color-bg)' }}><Spinner size={22} /></div>;
  }
  if (me && !me.onboarded) {
    return <RolePicker name={me.name || me.email} onDone={t => setMe({ ...me, track: t, onboarded: true })} />;
  }
  return <TrackContext.Provider value={me?.track ?? null}>{children}</TrackContext.Provider>;
}

function RolePicker({ name, onDone }: { name?: string; onDone: (track: string) => void }) {
  const [busy, setBusy] = React.useState<string | null>(null);
  const pick = async (id: string) => {
    setBusy(id);
    try {
      await api.setTrack(id);
      phCapture('track_selected', { track: id });
      phSetPerson({ track: id });
      onDone(id);
    } catch { setBusy(null); }
  };
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--color-row-hover)', padding: '24px' }}>
      <div style={{ width: 'min(680px, 100%)', textAlign: 'center' }}>
        <div style={{ width: '44px', height: '44px', borderRadius: '11px', background: 'var(--color-brand)', color: '#fff', display: 'grid', placeItems: 'center', fontSize: '18px', fontWeight: 800, margin: '0 auto 16px' }}>JP</div>
        <h1 style={{ margin: '0 0 6px', fontSize: '22px', fontWeight: 700 }}>Welcome{name ? `, ${name.split(' ')[0]}` : ''} 👋</h1>
        <p style={{ margin: '0 0 28px', color: 'var(--color-text-2)', fontSize: '14px' }}>
          Pick the track you&apos;re job-hunting in. We&apos;ll show you only those roles — you choose once.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
          {TRACKS.map(t => (
            <button key={t.id} onClick={() => pick(t.id)} disabled={!!busy}
              style={{
                textAlign: 'left', background: 'var(--color-bg)', border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-lg)', padding: '22px 20px', cursor: busy ? 'default' : 'pointer',
                boxShadow: 'var(--shadow-sm)', transition: 'border-color .15s, box-shadow .15s', position: 'relative',
              }}
              onMouseEnter={e => { if (!busy) { e.currentTarget.style.borderColor = 'var(--color-brand)'; e.currentTarget.style.boxShadow = 'var(--shadow-md)'; } }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-border)'; e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; }}>
              <span style={{ display: 'inline-grid', placeItems: 'center', width: '44px', height: '44px', borderRadius: '11px', background: 'var(--color-brand-subtle)', color: 'var(--color-brand)', marginBottom: '14px' }}>
                <svg width="30" height="30" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">{t.icon}</svg>
              </span>
              <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '6px' }}>{t.title}</div>
              <div style={{ fontSize: '13px', color: 'var(--color-text-2)', lineHeight: 1.5 }}>{t.desc}</div>
              {busy === t.id && <span style={{ position: 'absolute', top: '16px', right: '16px' }}><Spinner size={16} /></span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
