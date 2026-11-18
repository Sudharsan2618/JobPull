'use client';
import React, { ReactNode } from 'react';

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
      gap: '16px', flexWrap: 'wrap', padding: '24px 28px 0',
    }}>
      <div>
        <h1 style={{ margin: 0, fontSize: '22px', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--color-text-1)' }}>{title}</h1>
        {subtitle && <p style={{ margin: '4px 0 0', color: 'var(--color-text-2)', fontSize: '13px' }}>{subtitle}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>{actions}</div>}
    </div>
  );
}
