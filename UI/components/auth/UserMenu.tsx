'use client';
import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';

export function UserMenu() {
  const { user, logout } = useAuth0();
  const [open, setOpen] = React.useState(false);
  const label = user?.name || user?.email || 'Account';
  const initials = (user?.name || user?.email || 'JP').trim().slice(0, 2).toUpperCase();

  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} title={user?.email || ''} aria-label="Account menu"
        style={{ width: '30px', height: '30px', borderRadius: '50%', border: 'none', cursor: 'pointer', overflow: 'hidden', padding: 0, background: 'var(--color-brand-subtle)', color: 'var(--color-brand-text)', display: 'grid', placeItems: 'center', fontSize: '12px', fontWeight: 700 }}>
        {user?.picture ? <img src={user.picture} alt="" width={30} height={30} style={{ display: 'block', objectFit: 'cover' }} /> : initials}
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 60 }} />
          <div style={{ position: 'absolute', right: 0, top: '38px', zIndex: 61, width: '220px', background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-lg)', overflow: 'hidden' }}>
            <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '13px', fontWeight: 650, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</div>
              {user?.email && <div style={{ fontSize: '12px', color: 'var(--color-text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.email}</div>}
            </div>
            <button onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
              style={{ width: '100%', textAlign: 'left', padding: '10px 14px', border: 'none', background: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--color-text-1)', fontFamily: 'var(--font-sans)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'none')}>
              Log out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
