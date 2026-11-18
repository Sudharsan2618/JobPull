"""
Greenhouse connector — public boards API, no key required.

  list+content: GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

`content=true` returns the full description inline, so there's no separate enrich
step. Location is filtered client-side against the target cities (Greenhouse has
no server-side city facet), and date via `updated_at`.
"""
import html
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    requests = None

_UA = {"User-Agent": "Mozilla/5.0 (JobPull greenhouse)"}


def _normalize(j: Dict[str, Any], company: Dict[str, Any], loc: str, desc: str) -> Dict[str, Any]:
    token = company["token"]
    return {
        "source": "greenhouse", "title": (j.get("title") or "").strip(), "company": company["name"],
        "location": loc, "date_posted": (j.get("updated_at") or "").strip(),
        "job_url": j.get("absolute_url", ""), "apply_url": j.get("absolute_url", ""),
        "company_url": company.get("careers_url", ""), "description": desc,
        "salary": {"raw": ""}, "job_type": "", "skills": [], "experience": "", "role_summary": "",
        "external_id": f"gh-{token}-{j.get('id')}", "search_title": "career_monitor",
        "search_location": "career_monitor", "ats": "greenhouse",
        "career_url": company.get("careers_url", ""), "department": "",
        "requisition_id": str(j.get("id", "")),
    }


def discover(company: Dict[str, Any], cities: List[str], max_age_days) -> List[Dict[str, Any]]:
    """Pull a Greenhouse board, keep only target-city jobs inside the date window."""
    if requests is None:
        raise RuntimeError("requests not installed")
    url = f"https://boards-api.greenhouse.io/v1/boards/{company['token']}/jobs?content=true"
    r = requests.get(url, headers=_UA, timeout=25)
    r.raise_for_status()
    jobs = r.json().get("jobs", [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)) if max_age_days else None
    cl = [c.lower() for c in (cities or [])]
    out = []
    for j in jobs:
        loc = ((j.get("location") or {}).get("name") or "").strip()
        if cl and not any(c in loc.lower() for c in cl):
            continue  # location is primary
        if cutoff:
            try:
                d = datetime.fromisoformat((j.get("updated_at") or "").replace("Z", "+00:00"))
                if d < cutoff:
                    continue
            except Exception:
                pass  # unparseable date -> keep (never silently lose)
        desc = html.unescape(re.sub(r"<[^>]+>", " ", j.get("content") or "")).strip()
        out.append(_normalize(j, company, loc, desc))
    return out
