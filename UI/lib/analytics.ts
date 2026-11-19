'use client';
import posthog from 'posthog-js';

let started = false;

export function initPostHog() {
  if (started || typeof window === 'undefined') return;
  // The project key is public (write-only ingestion), so a fallback is safe and
  // keeps analytics working even if the Vercel env var isn't set.
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY || 'phc_XLaGhC29NW7u4kHAS8bstbpIRizJMdpHtJsNanHajVw';
  if (!key) return;
  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
    capture_pageview: false,       // captured manually on route change
    capture_pageleave: true,
    person_profiles: 'identified_only',
  });
  // Tag every JobPull event so it's separable from other apps in this shared project.
  posthog.register({ app: 'jobpull' });
  started = true;
}

export function phCapture(event: string, props?: Record<string, unknown>) {
  try { if (started) posthog.capture(event, props); } catch { /* analytics never breaks the app */ }
}

export function phIdentify(id: string, props?: Record<string, unknown>) {
  try { if (started) posthog.identify(id, props); } catch {}
}

export function phSetPerson(props: Record<string, unknown>) {
  try { if (started) posthog.setPersonProperties(props); } catch {}
}

export function phPageview() {
  try { if (started) posthog.capture('$pageview'); } catch {}
}

export function phReset() {
  try { if (started) posthog.reset(); } catch {}
}
