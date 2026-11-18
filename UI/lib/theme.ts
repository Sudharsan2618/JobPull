'use client';
import { useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

/** Reads/sets the <html data-theme> attribute and mirrors it to localStorage.
 *  The initial attribute is applied pre-paint by the inline script in layout.tsx. */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => {
    let saved: Theme | null = null;
    try { saved = localStorage.getItem('jp-theme') as Theme | null; } catch {}
    const current = (document.documentElement.getAttribute('data-theme') as Theme) || saved || 'light';
    setTheme(current);
    document.documentElement.setAttribute('data-theme', current);
  }, []);

  const toggle = () => {
    setTheme(prev => {
      const next: Theme = prev === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('jp-theme', next); } catch {}
      return next;
    });
  };

  return [theme, toggle];
}
