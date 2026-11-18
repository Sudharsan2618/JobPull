'use client';
import React from 'react';
import { useTheme } from '@/lib/theme';

export function ThemeToggle() {
  const [theme, toggle] = useTheme();
  const dark = theme === 'dark';
  return (
    <button onClick={toggle} title={dark ? 'Switch to light' : 'Switch to dark'} aria-label="Toggle theme"
      style={{
        width: '34px', height: '34px', display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: '1px solid var(--color-border-2)', background: 'var(--color-bg)', color: 'var(--color-text-2)',
        borderRadius: 'var(--radius-md)', cursor: 'pointer',
      }}>
      {dark ? (
        <svg width="16" height="16" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="9" cy="9" r="3.6" /><path d="M9 1.5v1.8M9 14.7v1.8M1.5 9h1.8M14.7 9h1.8M3.8 3.8l1.3 1.3M12.9 12.9l1.3 1.3M3.8 14.2l1.3-1.3M12.9 5.1l1.3-1.3" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 10.5A6.5 6.5 0 1 1 7.5 3a5 5 0 0 0 7.5 7.5z" />
        </svg>
      )}
    </button>
  );
}
