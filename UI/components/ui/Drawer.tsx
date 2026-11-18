'use client';
import React, { ReactNode } from 'react';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  children?: ReactNode;
}

export function Drawer({ open, onClose, children }: DrawerProps) {
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 40, background: 'rgba(10,15,25,0.42)',
          opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none', transition: 'opacity 0.2s',
        }}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-hidden={!open}
        style={{
          position: 'fixed', top: 0, right: 0, height: '100vh', width: 'min(540px, 94vw)',
          background: 'var(--color-bg)', zIndex: 50, boxShadow: 'var(--shadow-lg)',
          transform: open ? 'none' : 'translateX(100%)', transition: 'transform 0.22s',
          display: 'flex', flexDirection: 'column',
        }}
      >
        {children}
      </aside>
    </>
  );
}
