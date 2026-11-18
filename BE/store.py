"""
Storage — writes normalized jobs into the SEPARATE 'job-pull-simple' database
(same MongoDB cluster as BE). Synchronous pymongo; this is a script, not a server.

Dedupe key: (source + job_url) when a URL exists, else a hash of
source|title|company|location. Upsert so re-runs don't duplicate.
"""
from datetime import datetime
from hashlib import sha1
from typing import Any, Dict, List

from pymongo import MongoClient, ASCENDING

import config
from title_filter import profiles_for


def get_collection():
    if not config.MONGODB_URI:
        raise ValueError("MONGODB_URI is not set")
    client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")  # fail fast if unreachable
    col = client[config.DB_NAME][config.JOBS_COLLECTION]
    col.create_index([("dedupeKey", ASCENDING)], unique=True, name="idx_dedupe")
    col.create_index([("source", ASCENDING)], name="idx_source")
    col.create_index([("accepted", ASCENDING), ("lastSeenAt", ASCENDING)],
                    name="idx_accepted_last_seen")
    return client, col


def _dedupe_key(job: Dict[str, Any]) -> tuple[str, str]:
    """
    Return (sha1_key, strategy).

    Priority — the platform's own job id is the source of truth, because
    LinkedIn/Naukri/Indeed are semantic searches: the SAME posting comes back
    under different search terms ('agentic ai' vs 'gen ai'). Keying on the job
    id collapses those into one stored job.

      1. source + external_id   (platform job id — most reliable)
      2. source + job_url        (fallback — URL still carries the id)
      3. source + title|company|location  (last resort)
    """
    src = job.get("source", "")
    ext = (job.get("external_id") or "").strip()
    if ext:
        return sha1(f"{src}|id|{ext}".encode("utf-8")).hexdigest(), "external_id"

    url = (job.get("job_url") or "").strip()
    if url:
        return sha1(f"{src}|url|{url}".encode("utf-8")).hexdigest(), "job_url"

    basis = "|".join([
        src,
        (job.get("title") or "").strip().lower(),
        (job.get("company") or "").strip().lower(),
        (job.get("location") or "").strip().lower(),
    ])
    return sha1(basis.encode("utf-8")).hexdigest(), "fingerprint"


def upsert_one(job: Dict[str, Any], col) -> str:
    """
    Upsert a single job by its id-based dedupeKey. Idempotent: createdAt is set
    once and source fields refresh on repeats. Returns 'inserted' or 'updated'.
    Safe to call from the main thread as pool tasks complete (streaming write).
    """
    now = datetime.utcnow()
    key, strategy = _dedupe_key(job)
    # Refresh source fields on every scrape. Preserve post-LLM evaluation
    # fields: the next raw scrape must not undo a prior experience rejection or
    # discard the grounded analysis attached by analyze.py.
    evaluation_fields = {"_id", "createdAt", "accepted", "rejectionReason", "analysis"}
    fields = {k: v for k, v in job.items() if k not in evaluation_fields}
    # `profiles` = tracks whose title filter accepts this title (genai/fresher).
    # Derived from the title, so it refreshes on every scrape alongside source fields.
    fields.update({"dedupeKey": key, "dedupeStrategy": strategy,
                   "updatedAt": now, "lastSeenAt": now,
                   "profiles": profiles_for(job.get("title", ""))})
    # Source fields are already applied by $set on inserts. Only fields that
    # are intentionally preserved on later scrapes belong in $setOnInsert.
    insert_fields = {k: v for k, v in job.items()
                     if k in {"accepted", "rejectionReason", "analysis"}}
    insert_fields["createdAt"] = now
    res = col.update_one(
        {"dedupeKey": key},
        # createdAt = first seen (once). lastSeenAt = present in THIS scrape —
        # updated every run so a date filter reflects "seen in that day's 24h".
        {"$setOnInsert": insert_fields, "$set": fields},
        upsert=True,
    )
    return "inserted" if res.upserted_id else "updated"


def store(jobs: List[Dict[str, Any]], col) -> Dict[str, int]:
    """
    Upsert jobs (already title-evaluated). The same job id seen more than once
    (across search terms or across runs) updates the existing doc instead of
    inserting a new one — createdAt is set once and source fields refresh.
    Returns counts.
    """
    inserted = duplicates = 0
    for job in jobs:
        if upsert_one(job, col) == "inserted":
            inserted += 1
        else:
            duplicates += 1
    return {"inserted": inserted, "duplicates": duplicates}
