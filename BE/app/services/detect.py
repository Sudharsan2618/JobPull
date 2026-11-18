"""
Auto-detection: a company careers URL -> which backend it really uses + the
endpoint to pull from. This is the "discover once, verify, don't guess" step,
automated.

How it works (no guessing from the company name):
  1. Fetch the careers page HTML (requests; Firecrawl fallback for JS-only pages).
  2. Scan the HTML + links for known ATS signatures and extract the connector
     coordinates (Workday host/tenant/site, Greenhouse/Lever/Ashby token, ...).
  3. verify() pulls a small live sample so the UI can prove it works before saving.

Returns a connector descriptor dict the pipeline understands.
"""
import re
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

import config

_UA = {"User-Agent": "Mozilla/5.0 (JobPull detector)"}
_TIMEOUT = 20

# ATS signatures: (type, regex over page HTML) -> named groups become connector fields.
_SIGNATURES = [
    ("workday", re.compile(r"https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_]+)", re.I)),
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_]+)", re.I)),
    ("greenhouse", re.compile(r"greenhouse\.io/embed/job_board\?for=([a-z0-9_]+)", re.I)),
    ("lever", re.compile(r"jobs\.lever\.co/([a-z0-9-]+)", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([a-z0-9-]+)", re.I)),
    ("smartrecruiters", re.compile(r"careers\.smartrecruiters\.com/([A-Za-z0-9-]+)", re.I)),
    ("teamtailor", re.compile(r"https?://([a-z0-9.-]*\.?teamtailor\.com|careers\.[a-z0-9.-]+/jobs/\d+)", re.I)),
    ("icims", re.compile(r"([a-z0-9-]+)\.icims\.com", re.I)),
]


def _fetch_html(url: str) -> str:
    """Raw HTML via requests; if it looks empty/JS-only, fall back to Firecrawl."""
    html = ""
    if requests is not None:
        try:
            r = requests.get(url, headers=_UA, timeout=_TIMEOUT)
            if r.status_code < 400:
                html = r.text or ""
        except Exception:
            html = ""
    # Firecrawl fallback renders JS so links injected client-side are visible too.
    if len(html) < 2000 or "myworkdayjobs" not in html and "greenhouse" not in html:
        fc_html = _firecrawl_html(url)
        if fc_html:
            html += "\n" + fc_html
    return html


def _firecrawl_html(url: str) -> str:
    if not config.FIRECRAWL_API_KEY:
        return ""
    try:
        from firecrawl import Firecrawl
        fc = Firecrawl(api_key=config.FIRECRAWL_API_KEY)
        res = fc.scrape(url, formats=["html", "links"])
        parts = []
        for attr in ("html", "links"):
            v = getattr(res, attr, None) if not isinstance(res, dict) else res.get(attr)
            if isinstance(v, list):
                parts.append("\n".join(str(x) for x in v))
            elif v:
                parts.append(str(v))
        return "\n".join(parts)
    except Exception:
        return ""


def detect(careers_url: str) -> Dict[str, Any]:
    """Detect the ATS/backend behind a careers URL. Returns a connector descriptor."""
    url = careers_url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    html = _fetch_html(url)

    for ats, rx in _SIGNATURES:
        m = rx.search(html)
        if not m:
            continue
        if ats == "workday":
            host, dc, site = m.group(1) + "." + m.group(2) + ".myworkdayjobs.com", m.group(2), m.group(3)
            return {"type": "workday", "careers_url": url, "host": f"{m.group(1)}.{dc}.myworkdayjobs.com",
                    "tenant": m.group(1), "site": site, "evidence": m.group(0)}
        if ats in ("greenhouse", "lever", "ashby", "smartrecruiters"):
            return {"type": ats, "careers_url": url, "token": m.group(1), "evidence": m.group(0)}
        if ats == "teamtailor":
            return {"type": "teamtailor", "careers_url": url, "evidence": m.group(0),
                    "note": "Listing may live on the company page; apply flow is Teamtailor."}
        if ats == "icims":
            return {"type": "icims", "careers_url": url, "evidence": m.group(0)}

    # Nothing matched a known ATS -> custom in-house portal (e.g. Accenture's own API).
    return {"type": "custom", "careers_url": url,
            "note": "No standard ATS detected — likely a custom in-house portal. "
                    "Inspect its network calls to wire a custom connector."}


def verify(descriptor: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
    """Pull a tiny live sample to confirm the descriptor works. Returns
    {ok, count, sample:[{title, location}], error?}."""
    t = descriptor.get("type")
    try:
        if t == "workday":
            from sources import workday_source
            desc = {"name": descriptor.get("name", descriptor["tenant"]), "host": descriptor["host"],
                    "tenant": descriptor["tenant"], "site": descriptor["site"]}
            data = workday_source._post(desc, {}, "", 0)
            posts = (data.get("jobPostings") or [])[:limit]
            return {"ok": bool(posts), "count": data.get("total", len(posts)),
                    "sample": [{"title": p.get("title"), "location": p.get("locationsText")} for p in posts]}
        if t == "greenhouse":
            url = f"https://boards-api.greenhouse.io/v1/boards/{descriptor['token']}/jobs"
            r = requests.get(url, headers=_UA, timeout=_TIMEOUT)
            js = r.json().get("jobs", [])
            return {"ok": bool(js), "count": len(js),
                    "sample": [{"title": j.get("title"), "location": (j.get("location") or {}).get("name")} for j in js[:limit]]}
        if t == "lever":
            url = f"https://api.lever.co/v0/postings/{descriptor['token']}?mode=json"
            js = requests.get(url, headers=_UA, timeout=_TIMEOUT).json()
            return {"ok": bool(js), "count": len(js),
                    "sample": [{"title": j.get("text"), "location": (j.get("categories") or {}).get("location")} for j in js[:limit]]}
        if t == "ashby":
            url = f"https://api.ashbyhq.com/posting-api/job-board/{descriptor['token']}"
            js = requests.get(url, headers=_UA, timeout=_TIMEOUT).json().get("jobs", [])
            return {"ok": bool(js), "count": len(js),
                    "sample": [{"title": j.get("title"), "location": j.get("location")} for j in js[:limit]]}
    except Exception as e:
        return {"ok": False, "count": 0, "sample": [], "error": f"{type(e).__name__}: {e}"}
    return {"ok": False, "count": 0, "sample": [],
            "error": f"No automatic verifier for type '{t}' yet — needs a manual connector."}
