'use client';
import React from 'react';

export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <span
      aria-label="loading"
      style={{
        display: 'inline-block', width: size, height: size,
        border: '2px solid var(--color-border-2)', borderTopColor: 'var(--color-brand)',
        borderRadius: '50%', animation: 'spin 0.7s linear infinite',
      }}
    />
  );
}
