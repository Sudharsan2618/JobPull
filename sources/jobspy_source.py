"""
JobSpy source — LinkedIn + Indeed, split into discovery and enrichment.

  discover((site, title, location))  -> list of listing dicts (fast)
      * linkedin: linkedin_fetch_description=False  (descriptions come later,
        per unique job, in enrich_linkedin — avoids re-fetching duplicates)
      * indeed:   description IS included in the listing, so no enrich step
      * country_indeed set, or Indeed returns US jobs

  enrich_linkedin(job) -> job with .description filled from LinkedIn's public
      guest job-posting endpoint (no auth). Failures leave description empty.
"""
import random
import re
import threading
import time
from typing import Any, Dict, List, Tuple

import requests
from jobspy import scrape_jobs

import config


# LinkedIn's guest endpoint throttles under burst. Gate all calls to a gentle
# rate across threads and retry on throttling (429/999/503) so descriptions
# don't silently come back empty.
class _LiGate:
    def __init__(self, rpm: int):
        self.iv = 60.0 / max(1, rpm)
        self.l = threading.Lock()
        self.n = 0.0

    def wait(self):
        with self.l:
            now = time.monotonic()
            if now < self.n:
                time.sleep(self.n - now)
                now = time.monotonic()
            self.n = now + self.iv


_LI_GATE = _LiGate(getattr(config, "LINKEDIN_RPM", 40))
_LI_MAX_RETRIES = getattr(config, "LINKEDIN_MAX_RETRIES", 4)

_COLUMNS = [
    "id", "site", "job_url", "job_url_direct", "title", "company",
    "location", "date_posted", "description", "company_url", "min_amount",
    "max_amount", "currency", "job_type",
]

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
_LI_GUEST = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"


def _s(v) -> str:
    return "" if v is None else str(v)


def _normalize(row: Dict[str, Any], site: str, title: str, location: str) -> Dict[str, Any]:
    return {
        "source": site,
        "title": _s(row.get("title")).strip(),
        "company": _s(row.get("company")).strip(),
        "location": _s(row.get("location")).strip(),
        "date_posted": _s(row.get("date_posted")),
        "job_url": _s(row.get("job_url") or row.get("job_url_direct")).strip(),
        # direct apply / external application link when the board exposes one
        "apply_url": _s(row.get("job_url_direct")).strip(),
        "company_url": _s(row.get("company_url")).strip(),
        "description": _s(row.get("description")),
        "salary": {
            "min": row.get("min_amount"),
            "max": row.get("max_amount"),
            "currency": _s(row.get("currency")),
        },
        "job_type": _s(row.get("job_type")),
        "skills": [],
        "experience": "",
        "external_id": _s(row.get("id")),
        "search_title": title,
        "search_location": location,
    }


def discover(task: Tuple[str, str, str]) -> List[Dict[str, Any]]:
    """task = (site, title, location). Returns normalized listings."""
    site, title, location = task
    df = scrape_jobs(
        site_name=[site],
        search_term=title,
        location=location,
        hours_old=config.HOURS_OLD,
        results_wanted=config.RESULTS_PER_SEARCH,
        country_indeed=config.COUNTRY_INDEED,
        linkedin_fetch_description=False,  # descriptions fetched later, per unique job
    )
    if df is None or df.empty:
        return []
    have = [c for c in _COLUMNS if c in df.columns]
    return [_normalize(r, site, title, location) for r in df[have].to_dict(orient="records")]


def _li_job_id(job: Dict[str, Any]) -> str:
    """LinkedIn numeric posting id from external_id ('li-<id>') or the URL."""
    ext = (job.get("external_id") or "").strip()
    m = re.search(r"(\d{6,})", ext)
    if m:
        return m.group(1)
    m = re.search(r"/jobs/view/(\d+)", job.get("job_url") or "")
    return m.group(1) if m else ""


def enrich_linkedin(job: Dict[str, Any]) -> Dict[str, Any]:
    """Fill job['description'] from the public guest endpoint. Rate-gated +
    retried on throttling. Never raises; leaves description empty only if the
    posting truly has none or all retries fail."""
    job_id = _li_job_id(job)
    if not job_id:
        return job
    for attempt in range(_LI_MAX_RETRIES):
        _LI_GATE.wait()
        try:
            r = requests.get(_LI_GUEST.format(job_id=job_id),
                             headers={"User-Agent": _UA}, timeout=20)
        except Exception:
            time.sleep(2 + attempt * 2)
            continue
        if r.status_code in (429, 999, 503):
            time.sleep(5 + attempt * 5 + random.uniform(0, 2))  # throttled — back off
            continue
        if r.status_code != 200:
            break  # 404 / gone — nothing to fetch
        for pat in (r'show-more-less-html__markup[^>]*>(.*?)</div>',
                    r'description__text[^>]*>(.*?)</section>'):
            m = re.search(pat, r.text, re.DOTALL)
            if m:
                text = re.sub(r"<[^>]+>", " ", m.group(1))
                job["description"] = re.sub(r"\s+", " ", text).strip()
                break
        break
    return job
