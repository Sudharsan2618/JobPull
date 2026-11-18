# UI — JobPull frontend

The production frontend (Next.js 14 + TypeScript) lands here in **Phase 2**.

It will consume the FastAPI backend in `../BE` (routes under `/api/*`) and reuse the
design system (tokens, `components/ui` kit) from the reference app. Until then, the
backend still serves the legacy console at `BE/web/console.html`.
