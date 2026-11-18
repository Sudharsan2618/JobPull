'use client';
import React from 'react';

interface BarListProps {
  items: [string, number][];
  /** When set, the value column shows a percentage of this denominator. */
  denom?: number;
  max?: number;
  emptyHint?: string;
}

export function BarList({ items, denom, max, emptyHint = 'No data yet.' }: BarListProps) {
  if (!items || items.length === 0) {
    return <div style={{ color: 'var(--color-text-3)', fontSize: '13px' }}>{emptyHint}</div>;
  }
  const peak = max ?? Math.max(...items.map(i => i[1]), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
      {items.map(([label, value]) => {
        const pct = Math.max(3, Math.round((value / peak) * 100));
        const shown = denom ? `${Math.round((value / denom) * 100)}%` : value;
        return (
          <div key={label} style={{ display: 'grid', gridTemplateColumns: '150px 1fr 46px', alignItems: 'center', gap: '10px', fontSize: '12.5px' }}>
            <span style={{ color: 'var(--color-text-1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>
            <span style={{ height: '16px', background: 'var(--color-brand)', borderRadius: '4px', width: `${pct}%`, minWidth: '3px' }} />
            <span className="mono" style={{ textAlign: 'right', color: 'var(--color-text-2)' }}>{shown}</span>
          </div>
        );
      })}
    </div>
  );
}
