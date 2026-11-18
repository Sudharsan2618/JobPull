'use client';
import React, { CSSProperties, ReactNode } from 'react';

type Variant = 'success' | 'danger' | 'warning' | 'info' | 'neutral' | 'brand';

const variants: Record<Variant, CSSProperties> = {
  success: { background: 'var(--color-success-bg)', color: 'var(--color-success-text)' },
  danger: { background: 'var(--color-danger-bg)', color: 'var(--color-danger-text)' },
  warning: { background: 'var(--color-warning-bg)', color: 'var(--color-warning-text)' },
  info: { background: 'var(--color-brand-subtle)', color: 'var(--color-brand-text)' },
  neutral: { background: 'var(--color-surface)', color: 'var(--color-text-2)' },
  brand: { background: 'var(--color-brand-subtle)', color: 'var(--color-brand)' },
};

interface BadgeProps {
  children?: ReactNode;
  variant?: Variant;
  size?: 'sm' | 'md';
  style?: CSSProperties;
}

export function Badge({ children, variant = 'neutral', size = 'sm', style: extra }: BadgeProps) {
  const s: CSSProperties = {
    display: 'inline-flex', alignItems: 'center',
    padding: size === 'sm' ? '3px 10px' : '4px 12px',
    borderRadius: 'var(--radius-full)',
    fontSize: size === 'sm' ? '11.5px' : '13px',
    fontWeight: 600, fontFamily: 'var(--font-sans)', whiteSpace: 'nowrap',
    ...variants[variant], ...extra,
  };
  return <span style={s}>{children}</span>;
}
