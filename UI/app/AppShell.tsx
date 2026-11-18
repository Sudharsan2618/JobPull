'use client';
import React from 'react';
import { usePathname } from 'next/navigation';
import { AppBar } from '@/components/shell/AppBar';
import { Sidebar } from '@/components/shell/Sidebar';
import { AuthWall } from '@/components/auth/AuthWall';
import { TrackGate } from '@/components/auth/TrackGate';

function viewFromPath(pathname: string): string {
  if (pathname === '/' || pathname === '') return 'overview';
  if (pathname.startsWith('/jobs')) return 'jobs';
  if (pathname.startsWith('/analytics')) return 'analytics';
  if (pathname.startsWith('/companies')) return 'companies';
  if (pathname.startsWith('/schedules')) return 'schedules';
  return 'overview';
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);
  const activeView = viewFromPath(pathname || '/');

  return (
    <AuthWall>
      <TrackGate>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
        <AppBar sidebarCollapsed={collapsed} />
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
          <Sidebar activeView={activeView} collapsed={collapsed} onToggleCollapse={() => setCollapsed(c => !c)} />
          <main style={{ flex: 1, overflow: 'auto', minWidth: 0, background: 'var(--color-row-hover)' }}>
            {children}
          </main>
        </div>
      </div>
      </TrackGate>
    </AuthWall>
  );
}
