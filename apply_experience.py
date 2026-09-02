"""
One-time bulk update: apply the >3-year experience rule to CURRENT accepted jobs.

  py -3.13 apply_experience.py            # dry run (no writes) — preview only
  py -3.13 apply_experience.py --apply    # actually update the database

Naukri uses its listing experience; Indeed/LinkedIn use the LLM-extracted range
(only meaningful for already-analyzed jobs). Jobs with no experience yet are left
accepted — they get judged later, post-LLM, by analyze.py.
"""
import sys
from datetime import datetime
from collections import defaultdict

from pymongo import MongoClient

import config
from experience_filter import evaluate_experience, experience_of, min_years


def main(argv):
    apply = "--apply" in argv
    col = MongoClient(config.MONGODB_URI)[config.DB_NAME][config.JOBS_COLLECTION]
    acc = list(col.find({"accepted": True}))

    per = defaultdict(lambda: {"keep": 0, "reject": 0, "unknown": 0})
    to_reject = []
    keep = unknown = 0
    for j in acc:
        exp = experience_of(j)
        ok, reason = evaluate_experience(exp)
        src = j.get("source", "?")
        if not ok:
            to_reject.append((j["_id"], reason))
            per[src]["reject"] += 1
        elif min_years(exp) is None:
            unknown += 1
            per[src]["unknown"] += 1
        else:
            keep += 1
            per[src]["keep"] += 1

    print(f"{'DRY RUN' if not apply else 'APPLYING'} — experience rule: reject if min > 3 years")
    print(f"  currently accepted: {len(acc)}")
    print(f"  keep (min<=3): {keep}   reject (min>3): {len(to_reject)}   unknown (kept): {unknown}")
    for src in ("linkedin", "indeed", "naukri"):
        p = per[src]
        print(f"    {src:9s}: keep={p['keep']}  reject={p['reject']}  unknown={p['unknown']}")

    if apply and to_reject:
        now = datetime.utcnow()
        for _id, reason in to_reject:
            col.update_one({"_id": _id},
                           {"$set": {"accepted": False, "rejectionReason": reason, "updatedAt": now}})
        remaining = col.count_documents({"accepted": True})
        print(f"\n  rejected {len(to_reject)} jobs. Accepted now: {remaining}")
    elif not apply:
        print("\n  (no changes written — re-run with --apply to update)")


if __name__ == "__main__":
    main(sys.argv[1:])
