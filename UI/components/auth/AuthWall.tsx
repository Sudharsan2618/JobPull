'use client';
import React from 'react';
import { Auth0Provider, useAuth0, type RedirectLoginOptions } from '@auth0/auth0-react';
import { setTokenGetter } from '@/lib/api';
import { Spinner } from '@/components/ui/Spinner';

const DOMAIN = process.env.NEXT_PUBLIC_AUTH0_DOMAIN || '';
const CLIENT_ID = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID || '';
const AUDIENCE = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE || '';

/** True when Auth0 is configured — AppBar uses it to show the user menu. */
export const AUTH_CONFIGURED = Boolean(DOMAIN && CLIENT_ID);

export function AuthWall({ children }: { children: React.ReactNode }) {
  const [origin, setOrigin] = React.useState('');
  React.useEffect(() => { setOrigin(window.location.origin); }, []);

  if (!AUTH_CONFIGURED) return <>{children}</>;   // auth not set up → open app
  if (!origin) return null;                       // wait for client-side origin

  return (
    <Auth0Provider
      domain={DOMAIN}
      clientId={CLIENT_ID}
      authorizationParams={{ redirect_uri: origin, audience: AUDIENCE }}
      cacheLocation="localstorage"
    >
      <Gate>{children}</Gate>
    </Auth0Provider>
  );
}

function Gate({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, error, loginWithRedirect, getAccessTokenSilently } = useAuth0();

  // Register the token getter synchronously during render — NOT in an effect.
  // Child data-fetch effects run before parent effects, so an effect here would
  // leave the first /api call tokenless (401). Writing to a module ref in render
  // is idempotent and guarantees the getter is set before any page mounts.
  setTokenGetter(isAuthenticated ? () => getAccessTokenSilently() : null);

  if (isLoading) return <Splash><Spinner size={22} /></Splash>;
  if (!isAuthenticated) return <LoginScreen error={error?.message} onLogin={loginWithRedirect} />;
  return <>{children}</>;
}

function Splash({ children }: { children: React.ReactNode }) {
  return <div style={{ height: '100vh', display: 'grid', placeItems: 'center', background: 'var(--color-bg)' }}>{children}</div>;
}

function LoginScreen({ onLogin, error }: { onLogin: (options?: RedirectLoginOptions) => void; error?: string }) {
  const [busy, setBusy] = React.useState(false);
  const google = () => { setBusy(true); onLogin({ authorizationParams: { connection: 'google-oauth2' } }); };
  return (
    <div style={{ height: '100vh', display: 'grid', placeItems: 'center', background: 'var(--color-row-hover)', padding: '16px' }}>
      <div style={{ width: 'min(400px, 100%)', background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)', padding: '32px 28px', textAlign: 'center' }}>
        <div style={{ width: '44px', height: '44px', borderRadius: '11px', background: 'var(--color-brand)', color: '#fff', display: 'grid', placeItems: 'center', fontSize: '18px', fontWeight: 800, margin: '0 auto 16px' }}>JP</div>
        <h1 style={{ margin: '0 0 6px', fontSize: '20px', fontWeight: 700 }}>Welcome to JobPull</h1>
        <p style={{ margin: '0 0 24px', color: 'var(--color-text-2)', fontSize: '13.5px', lineHeight: 1.5 }}>
          Fresher &amp; entry-level IT jobs in Chennai &amp; Bengaluru. Sign in to continue.
        </p>
        <button onClick={google} disabled={busy}
          style={{ width: '100%', height: '44px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '10px', border: '1px solid var(--color-border-2)', background: 'var(--color-bg)', color: 'var(--color-text-1)', borderRadius: 'var(--radius-md)', fontSize: '14px', fontWeight: 600, cursor: busy ? 'default' : 'pointer' }}>
          {busy ? <Spinner size={16} /> : <GoogleIcon />}
          Continue with Google
        </button>
        {error && <div style={{ marginTop: '14px', fontSize: '12.5px', color: 'var(--color-danger-text)' }}>{error}</div>}
        <p style={{ margin: '22px 0 0', fontSize: '11.5px', color: 'var(--color-text-3)' }}>Secured by Auth0 · PKCE</p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z" />
    </svg>
  );
}
