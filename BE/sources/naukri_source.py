"""
Naukri source — Firecrawl, split into discovery and enrichment.

  discover((title, location)) -> listing dicts (no descriptions). Builds the
      naukri search URL with jobAge=1 (last 24h), scrapes the grid, paginates
      via interact() with a URL-suffix fallback. One Firecrawl browser session
      per call -> at 2 workers that's 2 browsers = Firecrawl free-plan limit.

  enrich(job) -> job with full description. One Firecrawl scrape per job.
      Runs in a SEPARATE stage from discovery so the 2-browser cap is never
      exceeded. Never raises; failures leave the description empty.
"""
import json
import random
import re
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Tuple

import config

try:
    from firecrawl import Firecrawl
except ImportError:  # Keep pure unit tests importable without network extras.
    Firecrawl = None


# ── Global Firecrawl rate gate + retry ────────────────────────────────────
# Free plan caps requests/minute (~40) on top of the 2-browser concurrency.
# One shared gate across ALL threads enforces a minimum spacing between calls,
# so N workers can never exceed the per-minute budget. On a 429 we honor the
# server's "retry after Xs" instead of dropping the job.
class _RateGate:
    def __init__(self, rpm: int):
        self.min_interval = 60.0 / max(1, rpm)
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
                now = time.monotonic()
            self._next = now + self.min_interval


_GATE = _RateGate(config.FIRECRAWL_RPM)
_RETRY_AFTER_RE = re.compile(r"retry after (\d+)\s*s", re.I)


def _fc_call(fn, *args, **kwargs):
    """Run a Firecrawl call through the rate gate, retrying on rate-limit
    errors using the server-supplied backoff. Raises other errors as-is."""
    for attempt in range(config.FIRECRAWL_MAX_RETRIES):
        _GATE.wait()
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            if "rate limit" in msg.lower() or "429" in msg:
                m = _RETRY_AFTER_RE.search(msg)
                delay = (int(m.group(1)) if m else 8) + random.uniform(0.5, 2.0)
                print(f"[Firecrawl] rate-limited; backing off {delay:.1f}s "
                      f"(attempt {attempt + 1}/{config.FIRECRAWL_MAX_RETRIES})")
                time.sleep(delay)
                continue
            raise
    raise RuntimeError("Firecrawl rate limit: retries exhausted")

LISTINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title":      {"type": "string"},
                    "company":    {"type": "string"},
                    "salary":     {"type": "string"},
                    "location":   {"type": "string"},
                    "experience": {"type": "string"},
                    "skills":     {"type": "array", "items": {"type": "string"}},
                    "url":        {"type": "string"},
                },
                "required": ["title", "company"],
            },
        },
        "current_page":  {"type": "integer"},
        "total_pages":   {"type": "integer"},
        "has_next_page": {"type": "boolean"},
    },
    "required": ["jobs"],
}

DESCRIPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "role_summary":        {"type": "string"},
        "experience_required": {"type": "string"},
        "required_skills":     {"type": "array", "items": {"type": "string"}},
        "full_description":    {"type": "string"},
    },
}

NEXT_PAGE_CODE = """
const nextSelectors = ['a[class*="next"]','span[class*="next"]','button[class*="next"]',
    'a[title="Next"]','[class*="pagination"] a:last-child','li.next a','a.fright'];
let clicked = false;
for (const sel of nextSelectors) { const el = await page.$(sel); if (el) { await el.click(); clicked = true; break; } }
if (!clicked) {
    const els = await page.$$('a, button, span');
    for (const el of els) { const text = (await el.textContent() || '').trim().toLowerCase();
        if (text === 'next' || text === '>' || text === '›') { await el.click(); clicked = true; break; } }
}
if (clicked) {
    await page.waitForLoadState('domcontentloaded');
    try { await page.waitForSelector('.jobTuple, .job-tuple, article[class*="job"], [class*="jobCard"]', { timeout: 5000 }); }
    catch (_) { await page.waitForTimeout(1500); }
}
const url = page.url();
JSON.stringify({ clicked, url });
"""


def _safe_json(result) -> dict:
    raw = getattr(result, "json", None) or getattr(result, "JSON", None) or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    return raw if isinstance(raw, dict) else {}


def _safe_output(result) -> str:
    return getattr(result, "output", None) or getattr(result, "stdout", None) or ""


def _build_url(title: str, location: str) -> str:
    t_slug = re.sub(r"[\s-]+", "-", re.sub(r"[^a-z0-9\s-]", "", title.lower())).strip("-")
    l_slug = re.sub(r"[\s-]+", "-", re.sub(r"[^a-z0-9\s-]", "", location.lower())).strip("-")
    q_title = urllib.parse.quote(title)
    q_loc = urllib.parse.quote(location)
    if l_slug:
        return f"https://www.naukri.com/{t_slug}-jobs-in-{l_slug}?k={q_title}&l={q_loc}&jobAge=1"
    return f"https://www.naukri.com/{t_slug}-jobs?k={q_title}&jobAge=1"


def _naukri_job_id(url: str) -> str:
    """Naukri job pages end with a unique numeric id, e.g. ...-240726032056."""
    m = re.search(r"-(\d{6,})/?$", (url or "").strip())
    return f"nk-{m.group(1)}" if m else ""


def _fallback_pagination(fc: Firecrawl, search_url: str, existing: list, start_page: int) -> List[dict]:
    all_jobs = list(existing)
    path, _, query = search_url.partition("?")
    for page_num in range(start_page + 1, config.NAUKRI_MAX_PAGES + 1):
        page_url = f"{path}-{page_num}?{query}" if query else f"{path}-{page_num}"
        try:
            result = _fc_call(fc.scrape, page_url, formats=[{
                "type": "json", "schema": LISTINGS_SCHEMA,
                "prompt": "Extract every job listing on this Naukri page: title, company, salary, "
                          "location, experience, skills, url. has_next_page=true if a Next button exists.",
            }])
        except Exception as e:
            print(f"[Naukri-fallback] scrape failed p{page_num}: {e}")
            break
        data = _safe_json(result)
        jobs_page = data.get("jobs", [])
        if not jobs_page:
            break
        for j in jobs_page:
            j["page_number"] = page_num
        all_jobs.extend(jobs_page)
        if not data.get("has_next_page", True):
            break
    return all_jobs


def _collect(fc: Firecrawl, search_url: str) -> List[dict]:
    all_jobs: List[dict] = []
    page_num = 1
    try:
        result = _fc_call(fc.scrape, search_url, formats=[{
            "type": "json", "schema": LISTINGS_SCHEMA,
            "prompt": "Extract every job listing visible on this Naukri search results page. "
                      "For each: title, company, salary ('Not Disclosed' if missing), location, "
                      "experience, skill tags, and full job URL. Also current_page, total_pages, has_next_page.",
        }])
    except Exception as e:
        print(f"[Naukri] initial scrape failed: {e}")
        return []

    scrape_id = None
    metadata = getattr(result, "metadata", None)
    if metadata:
        scrape_id = getattr(metadata, "scrape_id", None) or getattr(metadata, "scrapeId", None)

    data = _safe_json(result)
    jobs_page = data.get("jobs", [])
    has_next = data.get("has_next_page", False)
    for j in jobs_page:
        j["page_number"] = page_num
    all_jobs.extend(jobs_page)

    if not scrape_id:
        return _fallback_pagination(fc, search_url, all_jobs, page_num)

    while has_next and page_num < config.NAUKRI_MAX_PAGES:
        page_num += 1
        try:
            interact = _fc_call(fc.interact, scrape_id, code=NEXT_PAGE_CODE)
        except Exception:
            return _fallback_pagination(fc, search_url, all_jobs, page_num - 1)
        try:
            nav = json.loads(_safe_output(interact) or "{}")
        except Exception:
            nav = {}
        if not nav.get("clicked"):
            break
        try:
            extract = _fc_call(fc.interact, scrape_id, prompt=(
                "Extract every job listing on the current Naukri page. Return JSON with jobs "
                "(title, company, salary, location, experience, skills, url), current_page, "
                "total_pages, has_next_page."))
        except Exception:
            return _fallback_pagination(fc, search_url, all_jobs, page_num - 1)
        raw = _safe_output(extract)
        try:
            page_data = json.loads(raw)
        except Exception:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            page_data = json.loads(m.group()) if m else {}
        jobs_page = page_data.get("jobs", [])
        has_next = page_data.get("has_next_page", False)
        for j in jobs_page:
            j["page_number"] = page_num
        all_jobs.extend(jobs_page)

    try:
        fc.stop_interaction(scrape_id)
    except Exception:
        pass
    return all_jobs


def _normalize(job: dict, title: str, location: str) -> Dict[str, Any]:
    url = str(job.get("url") or "").strip()
    return {
        "source": "naukri",
        "title": str(job.get("title") or "").strip(),
        "company": str(job.get("company") or "").strip(),
        "location": str(job.get("location") or "").strip(),
        "date_posted": "",   # grid has no exact date; jobAge=1 already scopes to 24h
        "job_url": url,
        "company_url": "",
        "description": "",   # filled later by enrich()
        "salary": {"raw": job.get("salary") or "Not Disclosed"},
        "job_type": "",
        "skills": job.get("skills") or [],
        "experience": job.get("experience") or "",
        "role_summary": "",
        "external_id": _naukri_job_id(url),
        "search_title": title,
        "search_location": location,
    }


def discover(task: Tuple[str, str]) -> List[Dict[str, Any]]:
    """task = (title, location). Returns normalized listings (no descriptions)."""
    if not config.FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY is not set")
    if Firecrawl is None:
        raise RuntimeError("firecrawl-py is not installed")
    title, location = task
    fc = Firecrawl(api_key=config.FIRECRAWL_API_KEY)
    url = _build_url(title, location)
    print(f"[Naukri] discover: {url}")
    jobs = _collect(fc, url)
    return [_normalize(j, title, location) for j in jobs]


def enrich(job: Dict[str, Any]) -> Dict[str, Any]:
    """Fill full description for one Naukri job. Never raises."""
    url = job.get("job_url")
    if not url:
        return job
    if Firecrawl is None:
        print("[Naukri] enrich skipped: firecrawl-py is not installed")
        return job
    try:
        fc = Firecrawl(api_key=config.FIRECRAWL_API_KEY)
        result = _fc_call(fc.scrape, url, formats=[{
            "type": "json", "schema": DESCRIPTION_SCHEMA,
            "prompt": "From this Naukri job page extract: role_summary (2-3 sentences), "
                      "experience_required, required_skills list, full_description.",
        }])
        desc = _safe_json(result)
        job["description"] = desc.get("full_description") or ""
        job["role_summary"] = desc.get("role_summary") or ""
        if not job.get("experience"):
            job["experience"] = desc.get("experience_required") or ""
        if desc.get("required_skills"):
            job["skills"] = desc["required_skills"]
    except Exception as e:
        print(f"[Naukri] enrich failed for {url}: {e}")
    return job
