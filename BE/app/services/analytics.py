"""
Analytics for the console — now scoped to a user's track and cached.

"Posted" is keyed on `createdAt` (first seen) so the trend shows genuinely new
postings. "Matched" = the job matches the given track (its `profiles` contains
the track; falls back to `accepted` when no track is given). Results are cached
in-process for a few seconds so repeated dashboard loads don't re-run the
aggregations (cheaper on Cloud Run).
"""
import time
from datetime import datetime, timezone, timedelta
from collections import Counter

from app.services import db, exclude

IST = "Asia/Kolkata"
_CACHE: dict = {}
_TTL = 45.0  # seconds


def _cached(key, fn):
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    val = fn()
    _CACHE[key] = (now, val)
    return val


def _match(track):
    # genai keeps its experience-gated `accepted` flag; fresher uses the
    # title-derived `profiles` tag.
    if track == "fresher":
        return {"profiles": "fresher"}
    return {"accepted": True}


def _matched_cond(track):
    if track == "fresher":
        return {"$cond": [{"$in": ["fresher", {"$ifNull": ["$profiles", []]}]}, 1, 0]}
    return {"$cond": ["$accepted", 1, 0]}


def _overview(track):
    j = db.jobs()
    m = _match(track)
    matched = j.count_documents(m)
    rejected = j.count_documents({"accepted": False})
    analyzed = j.count_documents({**m, "analysis": {"$exists": True}})
    by_source = {d["_id"]: d["n"] for d in j.aggregate([
        {"$match": m}, {"$group": {"_id": "$source", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}])}
    by_company = [{"company": d["_id"], "n": d["n"]} for d in j.aggregate([
        {"$match": m}, {"$group": {"_id": "$company", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 40}])]
    by_company = [c for c in by_company if not exclude.is_excluded(c["company"])][:12]
    return {"accepted": matched, "rejected": rejected, "analyzed": analyzed,
            "bySource": by_source, "byCompany": by_company}


def _ist_midnight_utc():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def _bucket(fmt, days_back, track):
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    rows = db.jobs().aggregate([
        {"$match": {"createdAt": {"$gte": since}}},
        {"$group": {
            "_id": {"$dateToString": {"format": fmt, "date": "$createdAt", "timezone": IST}},
            "posted": {"$sum": 1},
            "matched": {"$sum": _matched_cond(track)},
        }},
        {"$sort": {"_id": 1}},
    ])
    return [{"bucket": r["_id"], "posted": r["posted"], "matched": r["matched"]} for r in rows]


def _today(track):
    start = _ist_midnight_utc()
    posted = db.jobs().count_documents({"createdAt": {"$gte": start}})
    matched = db.jobs().count_documents({**_match(track), "createdAt": {"$gte": start}})
    return posted, matched


def summary(track=None):
    def build():
        o = _overview(track)
        posted, matched = _today(track)
        o["today"] = {"posted": posted, "matched": matched}
        o["daily"] = _bucket("%Y-%m-%d", 14, track)
        o["weekly"] = _bucket("%G-W%V", 56, track)
        o["monthly"] = _bucket("%Y-%m", 186, track)
        return o
    return _cached(("summary", track), build)


def rich(track=None):
    def build():
        from categorize import categorize, CATEGORIES
        from analytics_agg import aggregate
        acc = list(db.jobs().find(_match(track),
                   {"title": 1, "search_location": 1, "location": 1,
                    "source": 1, "analysis": 1, "company": 1}))
        locations = Counter((a.get("search_location") or (a.get("location") or "").split(",")[0] or "—") for a in acc)
        categories = Counter(categorize(a.get("title", "")) for a in acc)
        sources = Counter(a.get("source", "") for a in acc)
        analyzed = [a for a in acc if a.get("analysis")]
        agg = aggregate(analyzed)
        return {
            "denom": agg["denom"],
            "locations": dict(locations),
            "categories": {c: categories.get(c, 0) for c in CATEGORIES if categories.get(c, 0)},
            "sources": dict(sources),
            "market": agg["market"][:20],
            "buckets": agg["buckets"],
        }
    return _cached(("rich", track), build)
