'use client';
import React, { CSSProperties, ReactNode } from 'react';

interface CardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  danger?: boolean;
  bodyStyle?: CSSProperties;
  style?: CSSProperties;
}

export function Card({ title, subtitle, children, action, danger = false, bodyStyle, style: extra }: CardProps) {
  const borderColor = danger ? 'var(--color-danger-border)' : 'var(--color-border)';
  return (
    <div style={{
      background: 'var(--color-bg)', border: `1px solid ${borderColor}`,
      borderRadius: 'var(--radius-lg)', overflow: 'hidden', ...extra,
    }}>
      {(title || action) && (
        <div style={{
          padding: '14px 18px', borderBottom: `1px solid ${borderColor}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px',
        }}>
          <div>
            {title && <div style={{ fontSize: '14px', fontWeight: 700, color: danger ? 'var(--color-danger-text)' : 'var(--color-text-1)' }}>{title}</div>}
            {subtitle && <div style={{ fontSize: '12.5px', color: 'var(--color-text-2)', marginTop: '2px' }}>{subtitle}</div>}
          </div>
          {action && <div style={{ flexShrink: 0 }}>{action}</div>}
        </div>
      )}
      <div style={{ padding: '18px', ...bodyStyle }}>{children}</div>
    </div>
  );
}
