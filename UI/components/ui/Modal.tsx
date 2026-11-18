'use client';
import React, { ReactNode } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  width?: number;
}

export function Modal({ open, onClose, title, children, footer, width = 560 }: ModalProps) {
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 60, background: 'rgba(10,15,25,0.42)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '48px 16px', overflow: 'auto',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)',
          width: `min(${width}px, 100%)`, boxShadow: 'var(--shadow-modal)', overflow: 'hidden',
        }}
      >
        {title && (
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>{title}</h3>
            <span style={{ flex: 1 }} />
            <button onClick={onClose} aria-label="Close" style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '18px', color: 'var(--color-text-3)', lineHeight: 1 }}>✕</button>
          </div>
        )}
        <div style={{ padding: '18px 20px' }}>{children}</div>
        {footer && <div style={{ padding: '14px 20px', borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>{footer}</div>}
      </div>
    </div>
  );
}
