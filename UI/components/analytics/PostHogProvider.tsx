'use client';
import React from 'react';
import { usePathname } from 'next/navigation';
import { initPostHog, phPageview } from '@/lib/analytics';

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  React.useEffect(() => { initPostHog(); }, []);

  // Manual SPA pageview on route change (app-router navigations).
  const pathname = usePathname();
  React.useEffect(() => { if (pathname) phPageview(); }, [pathname]);

  return <>{children}</>;
}
