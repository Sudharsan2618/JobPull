import type { Metadata } from 'next';
import './globals.css';
import { AppShell } from './AppShell';
import { PostHogProvider } from '@/components/analytics/PostHogProvider';

export const metadata: Metadata = {
  title: 'JobPull',
  description: 'Fresher & entry job discovery — Chennai & Bengaluru',
};

// Set the theme before first paint so there is no light/dark flash.
const THEME_INIT = `(function(){try{var t=localStorage.getItem('jp-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body><PostHogProvider><AppShell>{children}</AppShell></PostHogProvider></body>
    </html>
  );
}
