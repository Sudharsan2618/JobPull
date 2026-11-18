'use client';
import React, { ReactNode } from 'react';

interface StatTileProps {
  label: string;
  value: ReactNode;
  caption?: ReactNode;
  accent?: boolean;
}

export function StatTile({ label, value, caption, accent = false }: StatTileProps) {
  return (
    <div style={{
      background: 'var(--color-bg)',
      border: `1px solid ${accent ? 'var(--color-brand)' : 'var(--color-border)'}`,
      borderRadius: 'var(--radius-lg)', padding: '16px 18px',
    }}>
      <div style={{ fontSize: '11.5px', color: 'var(--color-text-3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {label}
      </div>
      <div className="tnum" style={{ fontSize: '28px', fontWeight: 700, letterSpacing: '-0.02em', marginTop: '8px', lineHeight: 1, color: accent ? 'var(--color-brand)' : 'var(--color-text-1)' }}>
        {value}
      </div>
      {caption != null && <div style={{ fontSize: '12px', color: 'var(--color-text-2)', marginTop: '7px' }}>{caption}</div>}
    </div>
  );
}
