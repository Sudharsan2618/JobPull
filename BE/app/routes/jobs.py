"""/api/jobs — the Jobs screen: track-filtered, server-paginated, light rows.

Status and reason are TRACK-AWARE: a fresher-track user sees a job's fresher
verdict (its title matched the IT-fresher filter), not the GenAI `accepted` flag.
Without this, fresher-matched jobs showed "rejected" with GenAI reject reasons.

Cost/transfer optimizations:
  * server-side filtering (track, status, source, city, days) — no 800-row dumps
  * cursor projection excludes `description`; it's fetched on open via /api/jobs/{id}
  * pagination (page + limit, capped) returns {items, total, page, hasMore}
"""
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.services import db, exclude
from app.deps import current_user
from title_filter import evaluate_fresher

try:
    from skills_canon import canonical, BUCKETS as SKILL_BUCKETS
except Exception:  # skills_canon optional
    canonical, SKILL_BUCKETS = (lambda x: x), []

router = APIRouter(prefix="/api")

# The list needs these fields only — NOT `description` (large; lazy-loaded).
_LIST_PROJECTION = {
    "title": 1, "company": 1, "location": 1, "source": 1, "ats": 1,
    "accepted": 1, "rejectionReason": 1, "relevance": 1, "profiles": 1,
    "date_posted": 1, "createdAt": 1, "lastSeenAt": 1,
    "apply_url": 1, "job_url": 1, "skills": 1, "experience": 1,
    "analysis.experience_range": 1, "analysis.buckets": 1, "analysis.key_topics": 1,
}

# City -> location regex. Covers city, its aliases, the state name, and the
# 2-letter state code boards like Indeed use (e.g. "KA, IN", "TN, IN").
_CITY_PATTERNS = {
    "bengaluru": r"bengaluru|bangalore|karnataka|\bka\b",
    "chennai": r"chennai|tamil ?nadu|\btn\b",
}


def _canon_skills(a):
    seen, out = set(), []
    for b in SKILL_BUCKETS:
        for t in (a.get("buckets", {}).get(b) or []):
            c = canonical(t)
            if c and c.lower() not in seen:
                seen.add(c.lower()); out.append(c)
    for t in (a.get("key_topics") or []):
        c = canonical(t)
        if c and c.lower() not in seen:
            seen.add(c.lower()); out.append(c)
    return out


def _row(d, track):
    ca, ls = d.get("createdAt"), d.get("lastSeenAt")
    rel = d.get("relevance") or {}
    a = d.get("analysis") or {}
    profiles = d.get("profiles") or []

    if track == "fresher":
        matched = "fresher" in profiles
        reason = None if matched else evaluate_fresher(d.get("title", ""))[1]
        why = rel.get("reason")  # usually empty for fresher-only jobs
    else:  # genai
        matched = bool(d.get("accepted"))
        reason = d.get("rejectionReason")
        why = rel.get("reason")

    return {
        "id": str(d.get("_id")),
        "title": d.get("title", ""), "company": d.get("company", ""),
        "location": d.get("location", ""), "source": d.get("source", ""),
        "ats": d.get("ats", d.get("source", "")),
        "url": d.get("apply_url") or d.get("job_url", ""),
        "accepted": matched,
        "rejectionReason": reason,
        "relevance": {"reason": why, "seniority": rel.get("seniority"), "engine": rel.get("engine")},
        "experience": (a.get("experience_range") or d.get("experience") or ""),
        "skills": _canon_skills(a) if a else (d.get("skills") or []),
        "analyzed": bool(a),
        "datePosted": d.get("date_posted", ""),
        "createdAt": ca.isoformat() if ca else None,
        "lastSeenAt": (ls or ca).isoformat() if (ls or ca) else None,
    }


def _full(d, track):
    r = _row(d, track)
    r["description"] = (d.get("description") or "")[:4000]
    return r


@router.get("/jobs")
def list_jobs(status: str = "matched", source: str = "", city: str = "",
              days: int = 0, page: int = 1, limit: int = 50,
              includeAgencies: int = 0, user: dict = Depends(current_user)):
    limit = max(1, min(limit, 100))
    page = max(1, page)
    track = user.get("track") or "genai"

    q: dict = {}
    # matched/rejected are relative to the user's track.
    if status == "matched":
        q["profiles" if track == "fresher" else "accepted"] = "fresher" if track == "fresher" else True
    elif status == "rejected":
        q["profiles" if track == "fresher" else "accepted"] = {"$ne": "fresher"} if track == "fresher" else False
    # 'all' -> no status/track filter
    if source:
        q["source"] = source
    if city:
        pat = _CITY_PATTERNS.get(city.lower(), city)
        q["location"] = {"$regex": pat, "$options": "i"}
    if days:
        q["createdAt"] = {"$gte": datetime.now(timezone.utc) - timedelta(days=days)}

    jc = db.jobs()
    total = jc.count_documents(q)
    cur = (jc.find(q, _LIST_PROJECTION)
             .sort("lastSeenAt", -1)
             .skip((page - 1) * limit)
             .limit(limit))
    items = [_row(d, track) for d in cur]
    if not includeAgencies:
        items = [d for d in items if not exclude.is_excluded(d["company"])]
    return {"items": items, "total": total, "page": page, "pageSize": limit,
            "hasMore": page * limit < total}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, user: dict = Depends(current_user)):
    try:
        oid = ObjectId(job_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="bad id")
    d = db.jobs().find_one({"_id": oid})
    if not d:
        raise HTTPException(status_code=404, detail="not found")
    return _full(d, user.get("track") or "genai")
