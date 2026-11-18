'use client';
import React, { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  hint?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({ title, hint, icon }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: '8px', padding: '48px 20px', textAlign: 'center',
    }}>
      {icon && <div style={{ color: 'var(--color-text-3)', marginBottom: '4px' }}>{icon}</div>}
      <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-1)' }}>{title}</div>
      {hint && <div style={{ fontSize: '13px', color: 'var(--color-text-2)', maxWidth: '420px', lineHeight: 1.5 }}>{hint}</div>}
    </div>
  );
}
