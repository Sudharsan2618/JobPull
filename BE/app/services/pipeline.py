"""
The pipeline — one orchestrator for every career-page connector.

For each enabled company in the registry it runs the same recall-safe flow:

  discover (per connector; LOCATION is primary + date window)
    -> dedupe -> incremental (skip jobs already in the DB)
    -> title guard (drop junk/senior)
    -> enrich (full description)
    -> RELEVANCE (LLM yes/no, keyword fallback)
    -> store   -> record a run  -> Telegram digest of new matches

Connectors dispatched by `type`: 'workday' and 'greenhouse' are implemented;
others are recorded as pending so the UI can show they need a manual connector.
"""
from datetime import datetime, timezone

import config
from store import upsert_one, _dedupe_key
from title_filter import REJECT_KEYWORDS, SENIORITY_RE, _contains_any
from sources import workday_source, greenhouse_source

from app.services import db, relevance, notify
from app.services import companies as registry


# City name aliases — a job in "Bangalore" must match a target of "Bengaluru".
CITY_ALIASES = {"bengaluru": ["bangalore"], "bangalore": ["bengaluru"]}


def _expand_cities(cities):
    out = set()
    for c in (cities or []):
        cl = c.strip().lower()
        out.add(cl)
        for a in CITY_ALIASES.get(cl, []):
            out.add(a)
    return list(out)


def _title_guard(job):
    t = (job.get("title") or "").strip().lower()
    if not t:
        return False, "missing title"
    if _contains_any(t, REJECT_KEYWORDS):
        return False, "junk title"
    if SENIORITY_RE.search(t):
        return False, "senior/lead-level"
    return True, ""


def _discover(company, max_age_days):
    t = company.get("type")
    if t == "workday":
        desc = {"name": company["name"], "host": company["host"],
                "tenant": company["tenant"], "site": company["site"]}
        locs = workday_source.list_locations(desc)
        sel = workday_source.select_locations(locs, _expand_cities(company.get("cities")))
        if not sel:
            return []
        applied = {"locations": [l["id"] for l in sel]}
        return workday_source.discover_facets((desc, applied, max_age_days, company["name"]))
    if t == "greenhouse":
        return greenhouse_source.discover(company, _expand_cities(company.get("cities")), max_age_days)
    return []  # pending connector (custom / teamtailor / ...)


def _enrich(job):
    return workday_source.enrich(job) if job.get("source") == "workday" else job


def run(names=None, max_age_days=7, use_llm=True, send_digest=True):
    """Run the pipeline for some/all enabled companies. Returns (run_doc, matched)."""
    registry.seed_defaults()
    cos = [c for c in registry.list_all()
           if c.get("enabled", True) and (not names or c["name"] in names)]

    run_doc = {"startedAt": datetime.now(timezone.utc), "scope": [c["name"] for c in cos],
               "discovered": 0, "new": 0, "matched": 0, "byCompany": {}, "errors": []}
    matched = []
    col = db.jobs()

    for c in cos:
        pending = c.get("type") not in ("workday", "greenhouse")
        if pending:
            run_doc["byCompany"][c["name"]] = {"new": 0, "matched": 0, "note": "connector pending"}
            continue
        try:
            raw = _discover(c, max_age_days)
        except Exception as e:
            run_doc["errors"].append(f"{c['name']}: {type(e).__name__}: {e}")
            continue
        run_doc["discovered"] += len(raw)

        # dedupe within this pull
        seen, uniq = set(), []
        for j in raw:
            k, _ = _dedupe_key(j)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(j)

        # incremental: only process jobs we haven't stored yet
        ext = [j["external_id"] for j in uniq]
        known = set(d["external_id"] for d in
                    col.find({"external_id": {"$in": ext}}, {"external_id": 1}))
        new = [j for j in uniq if j["external_id"] not in known]
        run_doc["new"] += len(new)

        cmatch = 0
        for j in new:
            ok, reason = _title_guard(j)
            if not ok:
                j["accepted"] = False
                j["rejectionReason"] = reason
                j.pop("_wd_detail", None)
                upsert_one(j, col)
                continue
            j = _enrich(j)
            verdict = relevance.judge(j) if use_llm else relevance._keyword_fallback(j)
            j["relevance"] = verdict
            j["accepted"] = bool(verdict.get("relevant"))
            j["rejectionReason"] = None if j["accepted"] else verdict.get("reason")
            j.pop("_wd_detail", None)
            upsert_one(j, col)
            if j["accepted"]:
                cmatch += 1
                matched.append(j)

        run_doc["byCompany"][c["name"]] = {"new": len(new), "matched": cmatch}
        run_doc["matched"] += cmatch
        db.companies().update_one({"name": c["name"]},
                                  {"$set": {"lastPull": datetime.now(timezone.utc)}})

    run_doc["finishedAt"] = datetime.now(timezone.utc)
    if send_digest:
        notify.digest(matched, when="today")
    return run_doc, matched


# ── Stage runners: return a counts dict; the runner writes the run record. ──
def run_boards(sources=("linkedin", "indeed", "naukri")):
    """STAGE A — job boards (jobspy + naukri) with title rejection, via run.py."""
    import run as boards
    col = db.jobs()
    bt, ba = col.count_documents({}), col.count_documents({"accepted": True})
    errors = []
    try:
        boards.main(list(sources))
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
    return {"scope": ["boards: " + ", ".join(sources)],
            "discovered": max(0, col.count_documents({}) - bt),
            "new": max(0, col.count_documents({}) - bt),
            "matched": max(0, col.count_documents({"accepted": True}) - ba),
            "errors": errors}


def run_career_counts():
    """STAGE B — career pages; wraps run() and returns a counts dict."""
    doc, _ = run(max_age_days=int(getattr(config, "CAREER_MAX_AGE_DAYS", 7)),
                 use_llm=True, send_digest=True)
    return {"scope": ["career: " + ", ".join(doc["scope"])] if doc["scope"] else ["career"],
            "discovered": doc["discovered"], "new": doc["new"], "matched": doc["matched"],
            "byCompany": doc["byCompany"], "errors": doc["errors"]}


def run_analyze():
    """STAGE C — LLM extraction & analysis on newly accepted jobs, via analyze.py."""
    import analyze
    col = db.jobs()
    before = col.count_documents({"accepted": True, "analysis": {"$exists": True}})
    errors = []
    try:
        analyze.main([])
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
    after = col.count_documents({"accepted": True, "analysis": {"$exists": True}})
    return {"scope": ["analyze (LLM)"], "discovered": 0, "new": 0,
            "matched": max(0, after - before), "note": f"analyzed {after - before} jobs",
            "errors": errors}
