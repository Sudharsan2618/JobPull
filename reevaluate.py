"""
Re-apply the current title + experience filters to ALL stored jobs.

Use after tuning title_filter.py / experience_filter.py so existing data reflects
the new rules (e.g. reject senior/lead titles, accept Forward Deployed). Only
flips the accepted flag + rejectionReason; never re-scrapes or re-analyzes.

  py -3.13 reevaluate.py
"""
from datetime import datetime, timezone

import config
from pymongo import MongoClient
from title_filter import evaluate_title
from experience_filter import evaluate_experience, experience_of


def main():
    col = MongoClient(config.MONGODB_URI)[config.DB_NAME][config.JOBS_COLLECTION]
    jobs = list(col.find({}, {"title": 1, "source": 1, "experience": 1, "analysis": 1,
                              "accepted": 1, "rejectionReason": 1}))
    before_acc = sum(1 for j in jobs if j.get("accepted"))
    changed = to_rej = to_acc = 0

    for j in jobs:
        ok, reason = evaluate_title(j.get("title", ""))
        if ok:
            eok, ereason = evaluate_experience(experience_of(j))
            if not eok:
                ok, reason = False, ereason
        was = bool(j.get("accepted"))
        if ok != was or (not ok and j.get("rejectionReason") != reason):
            col.update_one({"_id": j["_id"]}, {"$set": {
                "accepted": ok,
                "rejectionReason": None if ok else reason,
                "updatedAt": datetime.now(timezone.utc),
            }})
            changed += 1
            if ok and not was:
                to_acc += 1
            if not ok and was:
                to_rej += 1

    after_acc = col.count_documents({"accepted": True})
    print(f"re-evaluated {len(jobs)} jobs")
    print(f"  accepted: {before_acc} -> {after_acc}")
    print(f"  newly rejected: {to_rej} | newly accepted: {to_acc} | docs changed: {changed}")


if __name__ == "__main__":
    main()
