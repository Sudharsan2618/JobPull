"""
Retroactively collapse title+company duplicates among ACCEPTED jobs in the DB.

For each group of accepted jobs sharing a normalized (title, company), keep the
best copy (analyzed first, then most recently seen) and mark the rest rejected.
Fixes data scraped before the scraper-level dedupe existed.

  py -3.13 dedupe_existing.py
"""
from datetime import datetime, timezone

import config
from pymongo import MongoClient
from dedupe_titles import tc_key


def _ts(d):
    x = d.get("lastSeenAt") or d.get("createdAt")
    try:
        return x.timestamp() if x else 0
    except Exception:
        return 0


def _score(d):
    return (1 if d.get("analysis") else 0, _ts(d))


def main():
    col = MongoClient(config.MONGODB_URI)[config.DB_NAME][config.JOBS_COLLECTION]
    acc = list(col.find({"accepted": True},
                        {"title": 1, "company": 1, "analysis": 1, "lastSeenAt": 1, "createdAt": 1}))
    groups = {}
    for d in acc:
        t, c = (d.get("title") or "").strip(), (d.get("company") or "").strip()
        if not t or not c:
            continue
        groups.setdefault(tc_key(t, c), []).append(d)

    now = datetime.now(timezone.utc)
    rejected = dup_groups = 0
    for items in groups.values():
        if len(items) < 2:
            continue
        dup_groups += 1
        items.sort(key=_score, reverse=True)   # best kept first
        for d in items[1:]:
            col.update_one({"_id": d["_id"]}, {"$set": {
                "accepted": False,
                "rejectionReason": "duplicate: same title & company",
                "updatedAt": now,
            }})
            rejected += 1

    print(f"duplicate groups collapsed: {dup_groups}")
    print(f"marked {rejected} duplicate jobs as rejected")
    print(f"accepted now: {col.count_documents({'accepted': True})}")


if __name__ == "__main__":
    main()
