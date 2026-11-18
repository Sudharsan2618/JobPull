'use client';
import React, { ReactNode } from 'react';
import Link from 'next/link';

const EXPANDED_W = 230;
const RAIL_W = 52;

const SI = ({ d }: { d: ReactNode }) => (
  <svg width={17} height={17} viewBox="0 0 18 18" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, display: 'block' }}>
    {d}
  </svg>
);

const IC = {
  overview: <SI d={<path d="M2.5 7.8L9 2.5L15.5 7.8V15.5H11.5V11H6.5V15.5H2.5V7.8Z" />} />,
  jobs: <SI d={<><rect x="2.5" y="5.5" width="13" height="9" rx="1.5" /><path d="M6.5 5.5V4a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 11.5 4v1.5" /><line x1="2.5" y1="9.5" x2="15.5" y2="9.5" /></>} />,
  analytics: <SI d={<><path d="M4 15.5V7M9 15.5V3M14 15.5V10" /><line x1="2" y1="15.5" x2="16" y2="15.5" /></>} />,
  companies: <SI d={<><rect x="3" y="2.5" width="8" height="13" rx="1" /><path d="M11 6.5h3.5v9" /><path d="M5.5 5.5h3M5.5 8h3M5.5 10.5h3" /></>} />,
  schedules: <SI d={<><rect x="2.5" y="3.5" width="13" height="12" rx="1.5" /><line x1="2.5" y1="7.5" x2="15.5" y2="7.5" /><line x1="6" y1="1.5" x2="6" y2="5.5" /><line x1="12" y1="1.5" x2="12" y2="5.5" /></>} />,
  collapse: <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block' }}><path d="M8 2L3.5 6.5L8 11" /><path d="M12 2L7.5 6.5L12 11" /></svg>,
  expand: <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block' }}><path d="M5 2L9.5 6.5L5 11" /><path d="M1 2L5.5 6.5L1 11" /></svg>,
};

const NAV = [
  { id: 'overview', label: 'Overview', href: '/', icon: IC.overview },
  { id: 'jobs', label: 'Jobs', href: '/jobs', icon: IC.jobs },
  { id: 'analytics', label: 'Analytics', href: '/analytics', icon: IC.analytics },
  { id: 'companies', label: 'Companies', href: '/companies', icon: IC.companies },
  { id: 'schedules', label: 'Schedules', href: '/schedules', icon: IC.schedules },
];

interface SidebarProps {
  activeView: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export function Sidebar({ activeView, collapsed, onToggleCollapse }: SidebarProps) {
  const [hovered, setHovered] = React.useState<string | null>(null);

  const itemStyle = (active: boolean, hov: boolean): React.CSSProperties => ({
    display: 'flex', alignItems: 'center', gap: '10px',
    padding: collapsed ? '0' : '8px 14px',
    margin: collapsed ? '2px auto' : '1px 8px',
    width: collapsed ? `${RAIL_W - 8}px` : 'auto',
    height: collapsed ? '36px' : 'auto',
    justifyContent: collapsed ? 'center' : 'flex-start',
    borderRadius: '8px', fontSize: '13.5px', fontWeight: 500,
    color: active ? 'var(--color-brand)' : 'var(--color-text-1)',
    background: active ? 'var(--color-brand-tint)' : hov ? 'var(--color-hover)' : 'transparent',
    cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap', overflow: 'hidden',
    transition: 'background 0.12s, color 0.12s', textDecoration: 'none',
  });

  return (
    <div style={{
      position: 'relative',
      width: `${collapsed ? RAIL_W : EXPANDED_W}px`,
      minWidth: `${collapsed ? RAIL_W : EXPANDED_W}px`,
      transition: 'width 0.2s ease, min-width 0.2s ease', flexShrink: 0,
    }}>
      <button onClick={onToggleCollapse} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        style={{
          position: 'absolute', right: '-13px', top: '14px', width: '26px', height: '26px',
          border: '1px solid var(--color-border)', background: 'var(--color-surface)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px',
          color: 'var(--color-text-3)', zIndex: 20, boxShadow: 'var(--shadow-sm)',
        }}>
        {collapsed ? IC.expand : IC.collapse}
      </button>

      <aside style={{
        width: '100%', height: '100%', background: 'var(--color-surface)',
        borderRight: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column',
        overflowY: 'auto', overflowX: 'hidden', padding: '12px 0',
      }}>
        {NAV.map(item => {
          const active = activeView === item.id;
          return (
            <Link key={item.id} href={item.href} title={collapsed ? item.label : undefined}
              style={itemStyle(active, hovered === item.id)}
              onMouseEnter={() => setHovered(item.id)} onMouseLeave={() => setHovered(null)}>
              <span style={{ color: active ? 'var(--color-brand)' : 'var(--color-text-2)', display: 'flex', flexShrink: 0 }}>
                {item.icon}
              </span>
              {!collapsed && <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</span>}
            </Link>
          );
        })}

        <div style={{ flex: 1 }} />

        {!collapsed && (
          <div style={{ padding: '12px 16px', fontSize: '11px', color: 'var(--color-text-3)', lineHeight: 1.5 }}>
            Chennai &amp; Bengaluru · last 24h
          </div>
        )}
      </aside>
    </div>
  );
}
