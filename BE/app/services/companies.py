"""
Company/connector registry — the list the UI manages (add / verify / remove /
update). Stored in the `companies` collection so it survives restarts and the
pipeline reads it to know what to pull.

A company document:
  { name, type, careers_url, host/tenant/site (workday) | token (greenhouse...),
    cities: [..], categories: [..], enabled: bool, status: 'verified'|'unverified',
    lastPull, lastSample, createdAt, updatedAt }
"""
from datetime import datetime, timezone

from app.services import db, detect


def _now():
    return datetime.now(timezone.utc)


def list_all():
    out = []
    for c in db.companies().find().sort("name", 1):
        c["_id"] = str(c["_id"])
        out.append(c)
    return out


def get(name):
    c = db.companies().find_one({"name": name})
    if c:
        c["_id"] = str(c["_id"])
    return c


def upsert(doc: dict) -> dict:
    """Add or update a company by name."""
    name = doc["name"]
    doc = {k: v for k, v in doc.items() if k != "_id"}
    doc["updatedAt"] = _now()
    db.companies().update_one(
        {"name": name},
        {"$set": doc, "$setOnInsert": {"createdAt": _now()}},
        upsert=True,
    )
    return get(name)


def remove(name) -> bool:
    return db.companies().delete_one({"name": name}).deleted_count > 0


def detect_and_verify(careers_url: str, name: str = "") -> dict:
    """Run auto-detection + a live sample. Used by the Add-company wizard."""
    d = detect.detect(careers_url)
    if name:
        d["name"] = name
    v = detect.verify(d) if d.get("type") in ("workday", "greenhouse", "lever", "ashby") else \
        {"ok": False, "count": 0, "sample": [], "error": "manual connector needed for type '%s'" % d.get("type")}
    d["verify"] = v
    d["status"] = "verified" if v.get("ok") else "unverified"
    return d


def verify_existing(name: str) -> dict:
    """Re-run verification for a saved company and persist the result."""
    c = get(name)
    if not c:
        return {"error": "not found"}
    v = detect.verify(c)
    db.companies().update_one({"name": name}, {"$set": {
        "status": "verified" if v.get("ok") else "unverified",
        "lastSample": v.get("sample", []), "updatedAt": _now()}})
    return v


def seed_defaults():
    """Seed the registry with the connectors we've validated, if empty."""
    if db.companies().count_documents({}) > 0:
        return 0
    defaults = [
        {"name": "Genpact", "type": "workday", "careers_url": "https://www.genpact.com/careers",
         "host": "genpact.wd108.myworkdayjobs.com", "tenant": "genpact", "site": "External_Careers",
         "cities": ["Chennai", "Bengaluru"],
         "categories": ["Technology Solutions and Services", "Data and Analytics"],
         "enabled": True, "status": "verified"},
    ]
    for d in defaults:
        upsert(d)
    return len(defaults)
