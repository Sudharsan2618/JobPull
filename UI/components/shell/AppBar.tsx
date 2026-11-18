'use client';
import React from 'react';
import { ThemeToggle } from './ThemeToggle';
import { AUTH_CONFIGURED } from '@/components/auth/AuthWall';
import { UserMenu } from '@/components/auth/UserMenu';
import { useTrack, TRACK_LABEL } from '@/components/auth/TrackGate';

interface AppBarProps {
  sidebarCollapsed: boolean;
}

function TrackPill() {
  const track = useTrack();
  if (!track) return null;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 11px',
      borderRadius: 'var(--radius-full)', background: 'var(--color-brand-subtle)',
      color: 'var(--color-brand-text)', fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
    }} title="Your track (chosen at signup)">
      {TRACK_LABEL[track] || track}
    </span>
  );
}

export function AppBar({ sidebarCollapsed }: AppBarProps) {
  const brandW = sidebarCollapsed ? 52 : 230;
  return (
    <header style={{
      height: 'var(--size-appbar)', display: 'flex', alignItems: 'center',
      borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg)', zIndex: 50, flexShrink: 0,
    }}>
      <div style={{
        width: `${brandW}px`, minWidth: `${brandW}px`, display: 'flex', alignItems: 'center',
        gap: sidebarCollapsed ? '0' : '9px', padding: sidebarCollapsed ? '0' : '0 14px',
        justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
        borderRight: '1px solid var(--color-border)', height: '100%', overflow: 'hidden',
        transition: 'width 0.2s ease, min-width 0.2s ease, padding 0.2s ease', flexShrink: 0,
      }}>
        <span style={{
          width: '26px', height: '26px', borderRadius: '7px', background: 'var(--color-brand)', color: '#fff',
          display: 'grid', placeItems: 'center', fontSize: '13px', fontWeight: 800, flexShrink: 0,
        }}>JP</span>
        {!sidebarCollapsed && (
          <span style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--color-text-1)', whiteSpace: 'nowrap' }}>
            JobPull
          </span>
        )}
      </div>

      <div style={{ flex: 1 }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '0 16px' }}>
        <TrackPill />
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          fontSize: '12px', color: 'var(--color-text-2)',
        }}>
          <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--color-success)', boxShadow: '0 0 0 3px var(--color-success-bg)' }} />
          live
        </span>
        <ThemeToggle />
        {AUTH_CONFIGURED ? <UserMenu /> : (
          <span style={{
            width: '30px', height: '30px', borderRadius: '50%', background: 'var(--color-brand-subtle)',
            color: 'var(--color-brand-text)', display: 'grid', placeItems: 'center',
            fontSize: '12px', fontWeight: 700, cursor: 'default',
          }} title="Sign in not configured">JP</span>
        )}
      </div>
    </header>
  );
}
