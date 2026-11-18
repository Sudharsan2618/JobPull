"""/api/jobs — the Jobs screen: track-filtered, server-paginated, light rows.

Cost/transfer optimizations:
  * server-side filtering (track, status, source, city, days) — no 800-row dumps
  * cursor projection excludes `description` (the big field); it's fetched only
    when a job is opened, via GET /api/jobs/{id}
  * pagination (page + limit, capped) returns {items, total, page, hasMore}
"""
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.services import db, exclude
from app.deps import current_user

try:
    from skills_canon import canonical, BUCKETS as SKILL_BUCKETS
except Exception:  # skills_canon optional
    canonical, SKILL_BUCKETS = (lambda x: x), []

router = APIRouter(prefix="/api")

# The list needs these fields only — NOT `description` (large; lazy-loaded).
_LIST_PROJECTION = {
    "title": 1, "company": 1, "location": 1, "source": 1, "ats": 1,
    "accepted": 1, "rejectionReason": 1, "relevance": 1,
    "date_posted": 1, "createdAt": 1, "lastSeenAt": 1,
    "apply_url": 1, "job_url": 1, "skills": 1, "experience": 1,
    "analysis.experience_range": 1, "analysis.buckets": 1, "analysis.key_topics": 1,
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


def _row(d):
    ca, ls = d.get("createdAt"), d.get("lastSeenAt")
    rel = d.get("relevance") or {}
    a = d.get("analysis") or {}
    return {
        "id": str(d.get("_id")),
        "title": d.get("title", ""), "company": d.get("company", ""),
        "location": d.get("location", ""), "source": d.get("source", ""),
        "ats": d.get("ats", d.get("source", "")),
        "url": d.get("apply_url") or d.get("job_url", ""),
        "accepted": bool(d.get("accepted")),
        "rejectionReason": d.get("rejectionReason"),
        "relevance": {"reason": rel.get("reason"), "seniority": rel.get("seniority"), "engine": rel.get("engine")},
        "experience": (a.get("experience_range") or d.get("experience") or ""),
        "skills": _canon_skills(a) if a else (d.get("skills") or []),
        "analyzed": bool(a),
        "datePosted": d.get("date_posted", ""),
        "createdAt": ca.isoformat() if ca else None,
        "lastSeenAt": (ls or ca).isoformat() if (ls or ca) else None,
    }


def _full(d):
    r = _row(d)
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
    if status == "matched":
        # genai keeps its experience-gated `accepted` flag; fresher uses the
        # title-derived `profiles` tag (fresher has no pre-LLM experience gate).
        if track == "fresher":
            q["profiles"] = "fresher"
        else:
            q["accepted"] = True
    elif status == "rejected":
        q["accepted"] = False
    # 'all' -> no status/track filter
    if source:
        q["source"] = source
    if city:
        pat = "bengaluru|bangalore" if city.lower() == "bengaluru" else city
        q["location"] = {"$regex": pat, "$options": "i"}
    if days:
        q["createdAt"] = {"$gte": datetime.now(timezone.utc) - timedelta(days=days)}

    jc = db.jobs()
    total = jc.count_documents(q)
    cur = (jc.find(q, _LIST_PROJECTION)
             .sort("lastSeenAt", -1)
             .skip((page - 1) * limit)
             .limit(limit))
    items = [_row(d) for d in cur]
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
    return _full(d)
