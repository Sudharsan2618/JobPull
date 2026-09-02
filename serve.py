"""
JobPull frontend server — stdlib http.server + pymongo, no extra deps.

  python serve.py            # then open http://localhost:8000

Endpoints:
  GET /                      -> web/index.html
  GET /api/analytics         -> counts: locations, categories, sources, skills
  GET /api/jobs?status=accepted|rejected|all&q=&category=&source=&from=&to=
                             -> job list (with analysis if present)

Read-only against job-pull-simple.jobs. Does not run any scraper.
"""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from pymongo import MongoClient

import config
from categorize import categorize, CATEGORIES
from analytics_agg import aggregate
from skills_canon import canonical, BUCKETS as _CB

PORT = int(os.getenv("PORT", "8000"))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

_client = MongoClient(config.MONGODB_URI)
_col = _client[config.DB_NAME][config.JOBS_COLLECTION]

# The 5 buckets the user asked for + two the AI data warrants (added in Phase 2).
BUCKETS = ["skills_concepts", "frameworks", "methodologies", "cloud", "languages",
           "tools_platforms", "databases"]


def _canon_skills(a: dict) -> list:
    """Deduped canonical skills for a job, ordered by its buckets then topics."""
    seen, out = set(), []
    for b in _CB:
        for t in (a.get("buckets", {}).get(b) or []):
            c = canonical(t)
            if c and c.lower() not in seen:
                seen.add(c.lower()); out.append(c)
    for t in (a.get("key_topics") or []):
        c = canonical(t)
        if c and c.lower() not in seen:
            seen.add(c.lower()); out.append(c)
    return out


def _job_public(d: dict) -> dict:
    a = d.get("analysis") or {}
    ca = d.get("createdAt")
    return {
        "id": str(d.get("_id")),
        "title": d.get("title", ""),
        "company": d.get("company", ""),
        "location": d.get("location", ""),
        "searchLocation": d.get("search_location", ""),
        "source": d.get("source", ""),
        "url": d.get("job_url", ""),
        "applyUrl": d.get("apply_url", "") or d.get("job_url", ""),
        "companyUrl": d.get("company_url", ""),
        "category": categorize(d.get("title", "")),
        "accepted": bool(d.get("accepted")),
        "rejectionReason": d.get("rejectionReason"),
        "experience": (a.get("experience_range") or d.get("experience") or ""),
        "skills": d.get("skills") or [],
        "canonSkills": _canon_skills(a) if a else [],
        "description": d.get("description") or "",
        "analysis": a,
        "createdAt": ca.isoformat() if ca else None,
        "lastSeenAt": (d.get("lastSeenAt") or ca).isoformat() if (d.get("lastSeenAt") or ca) else None,
    }


def analytics() -> dict:
    acc = list(_col.find({"accepted": True},
                         {"title": 1, "search_location": 1, "source": 1, "analysis": 1}))
    rej_count = _col.count_documents({"accepted": False})

    locations = Counter(a.get("search_location", "") for a in acc)
    categories = Counter(categorize(a.get("title", "")) for a in acc)
    sources = Counter(a.get("source", "") for a in acc)

    # Canonicalized skill analytics (Layer 0): unique-job counts, single bucket.
    analyzed_jobs = [a for a in acc if a.get("analysis")]
    agg = aggregate(analyzed_jobs)

    return {
        "totals": {"accepted": len(acc), "rejected": rej_count, "analyzed": agg["denom"]},
        "denom": agg["denom"],
        "locations": dict(locations),
        "categories": {c: categories.get(c, 0) for c in CATEGORIES if categories.get(c, 0)},
        "sources": dict(sources),
        "market": agg["market"][:60],
        "buckets": agg["buckets"],
    }


def _parse_date(s: str):
    """Try to parse a date string into a datetime object. Returns None on failure."""
    s = s.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def jobs(params) -> list:
    status = (params.get("status", ["accepted"])[0]).lower()
    q = (params.get("q", [""])[0]).strip().lower()
    category = params.get("category", [""])[0]
    source = params.get("source", [""])[0]
    date_from = params.get("from", [""])[0]
    date_to = params.get("to", [""])[0]

    query = {}
    if status == "accepted":
        query["accepted"] = True
    elif status == "rejected":
        query["accepted"] = False

    if source:
        query["source"] = source

    # Date filter on lastSeenAt = "present in that day's scrape" (falls back to
    # createdAt for any legacy doc that predates the field).
    dt_from = _parse_date(date_from)
    dt_to = _parse_date(date_to)
    if dt_from or dt_to:
        date_q = {}
        if dt_from:
            date_q["$gte"] = dt_from
        if dt_to:
            date_q["$lte"] = dt_to.replace(hour=23, minute=59, second=59, microsecond=999999)
        query["$or"] = [
            {"lastSeenAt": date_q},
            {"lastSeenAt": {"$exists": False}, "createdAt": date_q},
        ]

    docs = [_job_public(d) for d in _col.find(query).limit(2000)]
    if category:
        docs = [d for d in docs if d["category"] == category]
    if q:
        docs = [d for d in docs if q in d["title"].lower() or q in d["company"].lower()]
    docs.sort(key=lambda d: (d["category"], d["company"]))
    return docs


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # quiet

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/analytics":
                return self._send(200, json.dumps(analytics()))
            if u.path == "/api/jobs":
                return self._send(200, json.dumps(jobs(parse_qs(u.query))))
            return self._send(404, json.dumps({"error": "not found"}))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


if __name__ == "__main__":
    print(f"JobPull UI:  http://localhost:{PORT}   (db={config.DB_NAME})")
    print("Ctrl+C to stop.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
