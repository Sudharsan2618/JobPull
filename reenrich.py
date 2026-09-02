"""
Backfill descriptions for ACCEPTED jobs that are still missing one (e.g. the
Firecrawl rate-limit casualties from an earlier run). Targets only the gaps —
no re-scraping of listings. Rate-gated + retrying, so it won't re-trip limits.

  python reenrich.py                 # all sources with gaps
  python reenrich.py naukri          # one source
"""
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import config
from store import get_collection
from pool import run_pool
from sources import jobspy_source, naukri_source

ENRICHERS = {
    "naukri": naukri_source.enrich,
    "linkedin": jobspy_source.enrich_linkedin,
    # indeed descriptions come with the listing — nothing to backfill
}


def main(argv):
    sources = [s.lower() for s in argv] or ["naukri", "linkedin"]
    client, col = get_collection()
    updated = {"count": 0}

    def writeback(job):
        col.update_one(
            {"_id": job["_id"]},
            {"$set": {
                "description": job.get("description") or "",
                "skills": job.get("skills") or [],
                "experience": job.get("experience") or "",
                "role_summary": job.get("role_summary") or "",
                "updatedAt": datetime.utcnow(),
            }},
        )
        if (job.get("description") or "").strip():
            updated["count"] += 1

    try:
        for src in sources:
            enricher = ENRICHERS.get(src)
            if not enricher:
                print(f"[reenrich] {src}: no enricher, skipping")
                continue
            gaps = list(col.find({
                "source": src, "accepted": True,
                "$or": [{"description": ""}, {"description": {"$exists": False}}],
            }))
            print(f"[reenrich] {src}: {len(gaps)} jobs missing descriptions")
            if not gaps:
                continue
            run_pool(gaps, enricher, config.WORKERS.get(src, 2),
                     on_result=writeback, label=f"reenrich-{src}")
    finally:
        client.close()

    print(f"\n[reenrich] filled {updated['count']} descriptions")


if __name__ == "__main__":
    main(sys.argv[1:])
