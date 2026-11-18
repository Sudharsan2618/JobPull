// Thin client for the FastAPI backend. In dev, Next rewrites /api/* to the
// backend origin (see next.config.mjs), so these are same-origin fetches.

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  source: string;
  ats: string;
  url: string;
  accepted: boolean;
  rejectionReason?: string | null;
  relevance?: { reason?: string | null; seniority?: string | null; engine?: string | null };
  experience?: string;
  skills?: string[];
  analyzed?: boolean;
  datePosted?: string;
  createdAt?: string | null;
  lastSeenAt?: string | null;
  description?: string;
}

export interface Analytics {
  today: { matched: number; posted: number };
  accepted: number;
  rejected: number;
  analyzed: number;
  bySource: Record<string, number>;
  byCompany: { company: string; n: number }[];
  daily?: { bucket: string; posted: number; matched: number }[];
  weekly?: { bucket: string; posted: number; matched: number }[];
  monthly?: { bucket: string; posted: number; matched: number }[];
}

export interface Market {
  categories: Record<string, number>;
  locations: Record<string, number>;
  market: [string, number][];
  buckets: Record<string, [string, number][]>;
  denom: number;
}

export interface Company {
  name: string;
  type: string;
  status?: string;
  host?: string;
  token?: string;
  careers_url?: string;
  cities?: string[];
  lastPull?: string | null;
}

export interface DetectResult {
  type: string;
  host?: string;
  token?: string;
  note?: string;
  verify?: { ok?: boolean; count?: number; error?: string; sample?: { title: string; location?: string }[] };
}

export interface JobsPage {
  items: Job[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface Me {
  sub: string;
  email: string;
  name: string;
  track: string | null;
  onboarded: boolean;
}

export interface Run {
  _id: string;
  status?: string;
  startedAt?: string;
  finishedAt?: string;
  scope?: string[];
  discovered: number;
  new: number;
  matched: number;
  errors?: string[];
}

// The AuthWall registers Auth0's token getter here so every /api call carries
// the access token. Null when auth is off or the user isn't signed in yet.
let _tokenGetter: (() => Promise<string>) | null = null;
export function setTokenGetter(fn: (() => Promise<string>) | null) { _tokenGetter = fn; }

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
  };
  if (_tokenGetter) {
    try { const t = await _tokenGetter(); if (t) headers.Authorization = `Bearer ${t}`; } catch { /* not signed in */ }
  }
  const r = await fetch(path, { ...init, headers });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json() as Promise<T>;
}

const get = <T>(path: string) => req<T>(path);
const post = <T>(path: string, body: unknown = {}) => req<T>(path, { method: 'POST', body: JSON.stringify(body) });
const del = <T>(path: string) => req<T>(path, { method: 'DELETE' });

export const api = {
  health: () => get<{ ok: boolean; schedule?: Array<{ next_run?: string }> }>('/api/health'),
  analytics: () => get<Analytics>('/api/analytics'),
  market: () => get<Market>('/api/analytics/market'),
  me: () => get<Me>('/api/me'),
  setTrack: (track: string) => post<Me>('/api/me/track', { track }),
  jobs: (params: { status?: string; source?: string; city?: string; days?: number; page?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set('status', params.status);
    if (params.source) q.set('source', params.source);
    if (params.city) q.set('city', params.city);
    if (params.days) q.set('days', String(params.days));
    if (params.page) q.set('page', String(params.page));
    if (params.limit) q.set('limit', String(params.limit));
    return get<JobsPage>('/api/jobs?' + q.toString());
  },
  job: (id: string) => get<Job>('/api/jobs/' + encodeURIComponent(id)),
  companies: () => get<Company[]>('/api/companies'),
  detectCompany: (url: string, name: string) => post<DetectResult>('/api/companies/detect', { url, name }),
  addCompany: (doc: Record<string, unknown>) => post('/api/companies', doc),
  verifyCompany: (name: string) => post(`/api/companies/${encodeURIComponent(name)}/verify`),
  deleteCompany: (name: string) => del(`/api/companies/${encodeURIComponent(name)}`),
  runs: (limit = 25) => get<Run[]>('/api/runs?limit=' + limit),
  runStage: (stage: 'boards' | 'career' | 'analyze') => post<{ started: boolean; error?: string }>('/api/run/' + stage),
};
