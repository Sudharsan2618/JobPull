"""
Small LIVE smoke test of the OPTIMIZED pipeline. Two overlapping titles in one
location so the id-based dedupe collapse is actually exercised. Then verifies
edge cases against what landed in Mongo.

  python tests/smoke_live.py            # all three
  python tests/smoke_live.py naukri     # one source
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# scope down (cheap) but keep TWO overlapping titles to trigger dedupe collapse
config.SEARCH_TITLES = ["AI Engineer", "Gen AI Engineer"]
config.SEARCH_LOCATIONS = ["Bangalore"]
config.RESULTS_PER_SEARCH = 8
config.NAUKRI_MAX_PAGES = 1
config.MAX_ENRICH_PER_SOURCE = 3   # cap enrichment cost

import run
from store import get_collection, _dedupe_key


def verify(sources):
    client, col = get_collection()
    problems = []
    try:
        docs = list(col.find({}))
        print(f"\n--- VERIFY ({len(docs)} docs in db) ---")

        # 1. no duplicate dedupeKey in storage
        keys = [d.get("dedupeKey") for d in docs]
        if len(keys) != len(set(keys)):
            problems.append("duplicate dedupeKey present in storage")
        print(f"  unique dedupeKeys: {len(set(keys))}/{len(keys)}")

        # 2. every doc recomputes to its stored key (id-based where possible)
        strat = {}
        for d in docs:
            k, s = _dedupe_key(d)
            strat[s] = strat.get(s, 0) + 1
            if k != d.get("dedupeKey"):
                problems.append(f"key mismatch for {d.get('title')}")
        print(f"  dedupe strategies: {strat}")

        # 3. accepted docs from enrichable sources should mostly have descriptions
        for src in sources:
            acc = [d for d in docs if d["source"] == src and d.get("accepted")]
            withdesc = [d for d in acc if (d.get("description") or "").strip()]
            print(f"  {src:9s}: accepted={len(acc)} with_description={len(withdesc)}")

        # 4. rejected docs are stored too (inspectable) and carry a reason
        rej = [d for d in docs if not d.get("accepted")]
        no_reason = [d for d in rej if not d.get("rejectionReason")]
        print(f"  rejected stored: {len(rej)} (missing reason: {len(no_reason)})")
        if no_reason:
            problems.append("rejected doc missing rejectionReason")

        # 5. no doc missing a title-quality flag or source
        for d in docs:
            if "accepted" not in d or not d.get("source"):
                problems.append(f"doc missing accepted/source: {d.get('_id')}")

        print("\n  EDGE-CASE RESULT:", "PASS" if not problems else f"ISSUES: {problems}")
    finally:
        client.close()
    return not problems


def main(argv):
    sources = [s.lower() for s in argv] or ["linkedin", "indeed", "naukri"]
    t0 = time.time()
    run.main(sources)
    print(f"\n[smoke] pipeline wall time: {time.time() - t0:.1f}s")
    verify(sources)


if __name__ == "__main__":
    main(sys.argv[1:])
