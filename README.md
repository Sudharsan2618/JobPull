# JobPull — monorepo

Job-pull engine + console for entry-to-mid roles in Chennai / Bengaluru.
Scrape → title filter → store → view.

## Layout

| Folder | What it is |
|--------|------------|
| `BE/` | FastAPI backend + scraping pipeline (Python 3.13). Serves the console and all `/api/*` endpoints; holds the batch entrypoints. |
| `UI/` | Production frontend — Next.js 14 + TypeScript. Added in Phase 2; consumes `BE` over `/api/*`. |
| `archive/` | One-off maintenance scripts and personal files. Kept locally, **gitignored**. |
| `deploy.ps1` | Google Cloud Run deployment. Build context is `BE/`. |
| `AUTH0_SETUP.md` | Auth0 (Google SSO) setup checklist for the login feature. |

---

## Backend (`BE/`)

Package management uses **[uv](https://docs.astral.sh/uv/)**.

```powershell
cd BE
uv venv                              # create .venv (Python 3.13)
uv pip install -r requirements.txt
```

Secrets live in `BE/.env` (`MONGODB_URI`, `FIRECRAWL_API_KEY`, `GEMINI_API_KEY`).
Data: MongoDB `job-pull-simple`, collection `jobs`.

### Run the console (API + current UI host)

```powershell
cd BE
.\.venv\Scripts\python.exe -m uvicorn app.server:app --port 8000
# then open http://localhost:8000
```

From the repo root, the in-app launch config runs the same server with `--app-dir BE`.
Thin by design: every route calls a service in `app/services`. The daily scheduler
starts with the app. The legacy stdlib server (`serve.py`, `web/index.html`) is what
the Docker image currently runs; the richer console is `app/server.py` + `web/console.html`.

### Pipeline (5 stages, `run.py`)

```
1. DISCOVER  parallel per-source thread pools   listings only, no descriptions
2. DEDUPE    in-memory, by platform job id      collapses semantic-search overlap
3. FILTER    titles only (title_filter.py)      drop non-matches before spending
4. ENRICH    parallel                           full descriptions for UNIQUE + ACCEPTED only
5. STORE     streaming upsert                    idempotent, writes as it goes
```

- **Concurrency** (`pool.py` + `config.WORKERS`): bounded thread pool per source. Naukri hard-capped at 2 (Firecrawl free-plan browser limit).
- **Title filter** (`title_filter.py`): `ACCEPT_KEYWORDS` / `REJECT_KEYWORDS` + a seniority guard. This is where the GenAI keyword set lives (and where the planned **IT-fresher** profile will add its own set).

### Batch entrypoints (in `BE/`)

| Script | Purpose |
|--------|---------|
| `run.py` | Nightly job-board pull (LinkedIn · Indeed · Naukri) |
| `pipeline.py` | Cloud Run Job entry — scrape + analyze |
| `run_career.py`, `run_workday.py` | Career-page / Workday sources |
| `view.py` | CLI viewer of stored jobs |
| `daily.py` | Daily driver |

### Tests

```powershell
cd BE
.\.venv\Scripts\python.exe tests/test_title_filter.py
.\.venv\Scripts\python.exe tests/test_dedupe.py
```

### Scope (hard-coded in `BE/config.py`)

- **Titles:** Gen AI Engineer, AI Engineer, Python Developer, Artificial Intelligence
- **Locations:** Chennai, Bengaluru
- **Time:** last 24 hours
- **Sources:** LinkedIn + Indeed (JobSpy), Naukri (Firecrawl)

---

## Frontend (`UI/`)

Next.js 14 + TypeScript production UI — **added in Phase 2**. Reuses a token-driven
design system (no Tailwind: CSS variables + a `components/ui` kit) and talks to `BE`'s
`/api/*`. Login is Auth0 with Google SSO (see `AUTH0_SETUP.md`).

---

## Deployment (Cloud Run)

From PowerShell with the Google Cloud CLI authenticated:

```powershell
.\deploy.ps1 -ProjectId YOUR_PROJECT_ID
```

- Build context is `BE/` (Dockerfile + requirements live there).
- Creates `jobpull-ui` (private Cloud Run service) and `jobpull-pipeline` (Cloud Run Job).
- `-AllowUnauthenticated` makes the dashboard public; `-EnableGemini` turns on analysis.
- A daily Cloud Scheduler trigger (default 06:00 Asia/Kolkata) is created/updated automatically.

Create these Secret Manager secrets first: `mongodb-uri`, `firecrawl-api-key`,
`gemini-api-key` (optional). The runtime service account needs
`roles/secretmanager.secretAccessor`.
