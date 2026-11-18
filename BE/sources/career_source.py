"""
Career Page Source — discovers company career URLs, monitors for new AI roles.

Integrates with JobPull pipeline:
  discover(task) -> list of listing dicts (no descriptions)
  enrich(job) -> job with full description (uses Firecrawl per job)

ATS-specific extraction for: greenhouse, lever, workday, ashby, smartrecruiters, generic.
"""
import json
import hashlib
import re
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Tuple, Optional

import config

try:
    from firecrawl import Firecrawl
except ImportError:  # Optional until the direct-site pipeline is enabled.
    Firecrawl = None


# ── Rate gate (reuse Firecrawl RPM limit) ──────────────────────────────────
class _RateGate:
    def __init__(self, rpm: int):
        self.min_interval = 60.0 / max(1, rpm)
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
                now = time.monotonic()
            self._next = now + self.min_interval


_GATE = _RateGate(config.FIRECRAWL_RPM)


def _fc_call(fn, *args, **kwargs):
    """Run Firecrawl call through rate gate with retry on 429."""
    for attempt in range(config.FIRECRAWL_MAX_RETRIES):
        _GATE.wait()
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e).lower()
            if "rate limit" in msg or "429" in msg:
                wait = 8 + attempt * 5
                print(f"[CareerPage] rate-limited; backing off {wait}s (attempt {attempt+1})")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Firecrawl retries exhausted")


# ── ATS Detection & URL Building ───────────────────────────────────────────

ATS_PATTERNS = {
    "greenhouse": r"boards\.greenhouse\.io/([^/?#]+)",
    "lever": r"jobs\.lever\.co/([^/?#]+)",
    "workday": r"([^\.]+)\.workday\.com",
    "ashby": r"jobs\.ashbyhq\.com/([^/?#]+)",
    "smartrecruiters": r"careers\.smartrecruiters\.com/([^/?#]+)",
    "icims": r"careers-[^\.]+\.icims\.com",
    "bamboohr": r"([^\.]+)\.bamboohr\.com",
    "recruitee": r"([^\.]+)\.recruitee\.com",
    "personio": r"([^\.]+)\.personio\.de",
    "teamtailor": r"([^\.]+)\.teamtailor\.com",
    "eightfold": r"careers\.eightfold\.ai/([^/?#]+)",
    "phenom": r"([^\.]+)\.phenompeople\.com",
}

# Known career page paths to try
CAREER_PATHS = [
    "/careers", "/jobs", "/join-us", "/work-with-us",
    "/about/careers", "/company/careers", "/en/careers",
    "/careers/", "/jobs/",
]


def detect_ats(url: str) -> str:
    """Detect ATS from career page URL."""
    for ats, pattern in ATS_PATTERNS.items():
        if re.search(pattern, url, re.I):
            return ats
    return "unknown"


def build_ats_url(company: Dict[str, str], ats: str) -> Optional[str]:
    """Build career URL for known ATS given company slug."""
    name = company["name"]
    domain = company.get("domain", "")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    
    # Try known ATS URL patterns
    if ats == "greenhouse":
        return f"https://boards.greenhouse.io/{slug}"
    elif ats == "lever":
        return f"https://jobs.lever.co/{slug}"
    elif ats == "ashby":
        return f"https://jobs.ashbyhq.com/{slug}"
    elif ats == "smartrecruiters":
        return f"https://careers.smartrecruiters.com/{slug}"
    elif ats == "workday":
        # Workday URLs vary wildly; try common patterns
        return f"https://{slug}.workday.com/en-US/jobs"
    elif ats == "recruitee":
        return f"https://{slug}.recruitee.com"
    elif ats == "teamtailor":
        return f"https://{slug}.teamtailor.com"
    
    return None


def try_common_paths(company: Dict[str, str]) -> List[str]:
    """Generate candidate career URLs from common paths."""
    domain = company.get("domain", "").strip()
    if not domain:
        return []
    domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
    base = f"https://{domain}"
    return [base + path for path in CAREER_PATHS]


# ── Extraction Schemas per ATS ─────────────────────────────────────────────

SCHEMAS = {
    "greenhouse": {
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "location": {"type": "string"},
                        "url": {"type": "string"},
                        "posted_date": {"type": "string"},
                        "department": {"type": "string"},
                        "absolute_url": {"type": "string"},
                    },
                },
            },
        },
    },
    "lever": {
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "location": {"type": "string"},
                        "url": {"type": "string"},
                        "posted_date": {"type": "string"},
                        "team": {"type": "string"},
                        "commitment": {"type": "string"},
                    },
                },
            },
        },
    },
    "ashby": {
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "location": {"type": "string"},
                        "url": {"type": "string"},
                        "posted_date": {"type": "string"},
                        "department": {"type": "string"},
                        "employment_type": {"type": "string"},
                    },
                },
            },
        },
    },
    "smartrecruiters": {
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "location": {"type": "string"},
                        "url": {"type": "string"},
                        "posted_date": {"type": "string"},
                        "department": {"type": "string"},
                        "job_function": {"type": "string"},
                    },
                },
            },
        },
    },
    "workday": {
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "location": {"type": "string"},
                        "url": {"type": "string"},
                        "posted_date": {"type": "string"},
                        "requisition_id": {"type": "string"},
                        "job_category": {"type": "string"},
                    },
                },
            },
        },
    },
    "generic": {
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "company": {"type": "string"},
                        "location": {"type": "string"},
                        "url": {"type": "string"},
                        "posted_date": {"type": "string"},
                        "description_snippet": {"type": "string"},
                    },
                },
            },
        },
    },
}

PROMPTS = {
    "greenhouse": "Extract ALL job postings from this Greenhouse board. For each job: title, location, full URL (absolute_url), posted date, department. Return jobs array.",
    "lever": "Extract ALL job postings from this Lever board. For each: title, location, full URL, posted date, team, commitment (full-time/contract). Return jobs array.",
    "ashby": "Extract ALL job postings from this Ashby board. For each: title, location, full URL, posted date, department, employment type. Return jobs array.",
    "smartrecruiters": "Extract ALL job postings from this SmartRecruiters career page. For each: title, location, full URL, posted date, department, job function. Return jobs array.",
    "workday": "Extract job postings from this Workday career site. For each: title, location, full URL, posted date, requisition ID, job category. Return jobs array. Note: Workday may need pagination.",
    "generic": "Extract ALL job postings visible on this career page. For each: title, company, location, full job URL, posted date, brief description snippet. Return jobs array.",
}


def _safe_json(result) -> dict:
    raw = getattr(result, "json", None) or getattr(result, "JSON", None) or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    return raw if isinstance(raw, dict) else {}


def scrape_career_page(fc: Firecrawl, url: str, ats: str) -> List[dict]:
    """Scrape a career page URL and extract job listings."""
    schema = SCHEMAS.get(ats, SCHEMAS["generic"])
    prompt = PROMPTS.get(ats, PROMPTS["generic"])
    
    try:
        result = _fc_call(fc.scrape, url, formats=[{
            "type": "json",
            "schema": schema,
            "prompt": prompt,
        }])
    except Exception as e:
        print(f"[CareerPage] scrape failed for {url}: {e}")
        return []
    
    data = _safe_json(result)
    return data.get("jobs", [])


def normalize_job(job: dict, company_name: str, career_url: str, ats: str) -> Dict[str, Any]:
    """Normalize extracted job to JobPull schema."""
    url = str(job.get("url") or job.get("absolute_url") or "").strip()
    
    # Generate external_id from URL
    external_id = ""
    if url:
        # Try to extract numeric ID from URL
        m = re.search(r"[/-](\d{6,})", url)
        if m:
            external_id = f"cp-{ats}-{m.group(1)}"
        else:
            stable_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
            external_id = f"cp-{ats}-{stable_id}"
    
    return {
        "source": "career_page",
        "title": str(job.get("title") or "").strip(),
        "company": company_name,
        "location": str(job.get("location") or "").strip(),
        "date_posted": str(job.get("posted_date") or "").strip(),
        "job_url": url,
        "apply_url": url,
        "company_url": career_url,
        "description": str(job.get("description_snippet") or job.get("description") or "").strip(),
        "salary": {"raw": ""},
        "job_type": str(job.get("commitment") or job.get("employment_type") or job.get("job_type") or "").strip(),
        "skills": [],
        "experience": "",
        "role_summary": "",
        "external_id": external_id,
        "search_title": "career_page_monitor",
        "search_location": "career_page_monitor",
        "ats": ats,
        "career_url": career_url,
        "department": str(job.get("department") or job.get("team") or job.get("job_category") or job.get("job_function") or "").strip(),
        "requisition_id": str(job.get("requisition_id") or "").strip(),
    }


# ── Public API: discover() ─────────────────────────────────────────────────

def discover(task: Tuple[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Pipeline entry point. Task = (company_dict,).
    Returns normalized job listings (no full descriptions).
    """
    if not config.FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY not set in config")
    if Firecrawl is None:
        raise RuntimeError("firecrawl-py is not installed")
    
    (company,) = task
    company_name = company["name"]
    known_ats = company.get("ats", "unknown")
    
    print(f"[CareerPage] Discovering: {company_name} (known ATS: {known_ats})")
    
    fc = Firecrawl(api_key=config.FIRECRAWL_API_KEY)
    all_jobs = []
    tried_urls = set()
    
    # Strategy 1: If known ATS, try direct ATS URL
    if known_ats != "unknown":
        ats_url = build_ats_url(company, known_ats)
        if ats_url and ats_url not in tried_urls:
            tried_urls.add(ats_url)
            print(f"  Trying known ATS URL: {ats_url}")
            jobs = scrape_career_page(fc, ats_url, known_ats)
            if jobs:
                print(f"  Found {len(jobs)} jobs via {known_ats}")
                for job in jobs:
                    all_jobs.append(normalize_job(job, company_name, ats_url, known_ats))
                return all_jobs  # Success, no need to try other URLs
    
    # Strategy 2: Try common career page paths
    for url in try_common_paths(company):
        if url in tried_urls:
            continue
        tried_urls.add(url)
        print(f"  Trying common path: {url}")
        
        # First, check if page exists and has jobs
        try:
            result = _fc_call(fc.scrape, url, formats=[{
                "type": "json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "has_jobs": {"type": "boolean"},
                        "ats_detected": {"type": "string"},
                        "job_count_estimate": {"type": "integer"},
                    },
                },
                "prompt": f"Does {url} have a job listings page? Return has_jobs (boolean), ats_detected (greenhouse/lever/workday/ashby/smartrecruiters/other), job_count_estimate.",
            }])
        except Exception as e:
            print(f"    Check failed: {e}")
            continue
        
        data = _safe_json(result)
        if not data.get("has_jobs"):
            print(f"    No jobs detected")
            continue
        
        detected_ats = data.get("ats_detected", "unknown").lower()
        if detected_ats not in SCHEMAS:
            detected_ats = "generic"
        
        print(f"    Detected ATS: {detected_ats}, est. jobs: {data.get('job_count_estimate', '?')}")
        
        # Now do full extraction
        jobs = scrape_career_page(fc, url, detected_ats)
        if jobs:
            print(f"    Extracted {len(jobs)} jobs")
            for job in jobs:
                all_jobs.append(normalize_job(job, company_name, url, detected_ats))
            return all_jobs  # First working URL wins
    
    print(f"  No career page found or no jobs extracted")
    return []


# ── Enrichment: fetch full job description ────────────────────────────────

DESCRIPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "full_description": {"type": "string"},
        "experience_required": {"type": "string"},
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "responsibilities": {"type": "string"},
        "qualifications": {"type": "string"},
    },
}

def enrich(job: Dict[str, Any]) -> Dict[str, Any]:
    """Fill full description for one career page job."""
    url = job.get("job_url")
    if not url:
        return job
    if Firecrawl is None:
        print("[CareerPage] enrich skipped: firecrawl-py is not installed")
        return job
    
    print(f"[CareerPage] Enriching: {job.get('title')} @ {job.get('company')}")
    
    try:
        fc = Firecrawl(api_key=config.FIRECRAWL_API_KEY)
        result = _fc_call(fc.scrape, url, formats=[{
            "type": "json",
            "schema": DESCRIPTION_SCHEMA,
            "prompt": "Extract from this job posting: full_description, experience_required, required_skills (list), responsibilities, qualifications.",
        }])
        data = _safe_json(result)
        
        job["description"] = data.get("full_description") or job.get("description") or ""
        job["role_summary"] = data.get("responsibilities") or ""
        if not job.get("experience"):
            job["experience"] = data.get("experience_required") or ""
        if data.get("required_skills"):
            job["skills"] = data["required_skills"]
            
    except Exception as e:
        print(f"[CareerPage] Enrich failed for {url}: {e}")
    
    return job
