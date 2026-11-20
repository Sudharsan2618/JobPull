"""
JobPull — simple config.

SELF-CONTAINED: all secrets come from this module's own JobPull/.env
(MONGODB_URI, FIRECRAWL_API_KEY, GEMINI_API_KEY). No reference to BE/.env.

Nothing here is derived or guessed — the search scope is hard-coded to exactly
what was asked: 4 titles, 2 locations, last 24 hours.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Secrets — this module's own .env only
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # legacy/optional

# Auth0 (login). Domain + audience are public; used to validate access tokens.
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "")

# PostHog — AI Observability for the pipeline's Gemini calls. Project key is public.
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")

# ---------------------------------------------------------------------------
# Extraction engine (Phase 2) — Google Gemini direct, grounded structured output.
#   Free tier (gemini-3.5-flash-lite): 15 RPM · 250K TPM · 500 requests/day.
#   Stay under 15 RPM; RPD (500) comfortably covers the whole backlog.
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_RPM = 13           # free tier is 15 RPM — keep a safe margin
GEMINI_MAX_RETRIES = 5
GEMINI_WORKERS = 6        # RPM-bound; the rate gate paces to GEMINI_RPM

# ---------------------------------------------------------------------------
# Separate database (same cluster) + single collection
# ---------------------------------------------------------------------------
DB_NAME = os.getenv("DB_NAME", "job-pull-simple")
JOBS_COLLECTION = os.getenv("JOBS_COLLECTION", "jobs")

# ---------------------------------------------------------------------------
# Search scope — EXACTLY as requested. Change here, nowhere else.
# ---------------------------------------------------------------------------
SEARCH_TITLES = [
    "Gen AI Engineer",
    "AI Engineer",
    "Python Developer",
    "Artificial Intelligence",
]

SEARCH_LOCATIONS = ["Chennai", "Bangalore"]

# ---------------------------------------------------------------------------
# IT-FRESHER profile — a second search scope for entry-level IT roles.
# The scraper uses these titles when run with profile="fresher"; the matching
# accept/reject rules live in title_filter.evaluate_fresher.
# ---------------------------------------------------------------------------
FRESHER_SEARCH_TITLES = [
    # ── Generic entry-level IT (kept broad on purpose — a "software developer"
    #    search pulls java/python/.net/php/react/etc. fresher roles, so no
    #    stack-specific keywords are needed). IT-scoped so boards return tech,
    #    not nursing/sales freshers.
    "IT Fresher",
    "Software Developer Fresher",
    "Software Engineer Fresher",
    "Graduate Engineer Trainee",
    "Trainee Software Engineer",
    "Associate Software Engineer",
    "Junior Software Developer",
    "Junior Software Engineer",
    "Junior Developer",
    "Junior Programmer",
    # ── QA / testing
    "Junior Software Tester",
    "QA Engineer Fresher",
    # ── Ops / infra / support
    "Junior DevOps Engineer",
    "Junior System Administrator",
    "Technical Support Fresher",
    # ── Data
    "Junior Data Analyst",
]

# Profile registry — maps a profile key to its label + search scope. The
# accept/reject logic for each lives in title_filter (evaluate / evaluate_fresher).
PROFILES = {
    "genai":   {"label": "GenAI roles", "search_titles": SEARCH_TITLES},
    "fresher": {"label": "IT Fresher",  "search_titles": FRESHER_SEARCH_TITLES},
}

HOURS_OLD = 24          # JobSpy hours_old + Naukri jobAge=1
RESULTS_PER_SEARCH = 50  # per (title x location x site) for JobSpy

# JobSpy Indeed needs the country; India locations return nothing without it.
COUNTRY_INDEED = "India"

# Naukri (Firecrawl) pagination cap per search URL
NAUKRI_MAX_PAGES = 5

# ---------------------------------------------------------------------------
# Concurrency — bounded thread pool per source (I/O-bound, blocking libs).
#   Firecrawl FREE plan = 2 concurrent browsers -> naukri MUST stay at 2.
#   LinkedIn blocks aggressively -> keep low.
# ---------------------------------------------------------------------------
WORKERS = {
    "linkedin": 2,
    "indeed": 3,
    "naukri": 2,   # hard cap: Firecrawl free plan allows 2 concurrent browsers
}

# Enrich full descriptions for UNIQUE + ACCEPTED jobs only.
ENRICH_DESCRIPTIONS = True
MAX_ENRICH_PER_SOURCE = None   # None = all unique+accepted; or an int cap

# Firecrawl FREE plan also caps REQUESTS PER MINUTE (~40), separate from the
# 2-browser concurrency cap. Keep a safe margin under it; all Firecrawl calls
# pass through a global rate gate + retry-on-429 honoring the server backoff.
FIRECRAWL_RPM = 30
FIRECRAWL_MAX_RETRIES = 6

# ---------------------------------------------------------------------------
# Career Page Monitoring — target companies (used ONLY by run_career.py,
# never by the nightly run.py flow).
#
# This is a SMALL TEST set, derived from companies that actually appear in the
# job-pull-simple DB (see target_companies_from_db.json for the full candidate
# list). ats="unknown" makes career_source auto-detect the ATS from the live
# page instead of guessing a wrong one. Stripe is a confident Greenhouse anchor.
# ---------------------------------------------------------------------------
TARGET_COMPANIES = [
    {"name": "Stripe",  "domain": "stripe.com",  "ats": "greenhouse"},  # in DB (16), reliable
    {"name": "NVIDIA",  "domain": "nvidia.com",  "ats": "unknown"},     # in DB (9), auto-detect
    {"name": "Genpact", "domain": "genpact.com", "ats": "unknown"},     # in DB (43), auto-detect
]

# Concurrency for career_page (Firecrawl-based, keep low)
WORKERS["career_page"] = 1
