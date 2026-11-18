"""
JobPull — STANDALONE Workday runner (location-primary, recall-safe).

  python run_workday.py                    # Chennai/Bengaluru jobs, last N days
  python run_workday.py --list-locations   # show each tenant's city offices matched
  python run_workday.py --list-categories  # show each tenant's job categories
  python run_workday.py --all-dates        # ignore the date window (full backfill)

FILTER ORDER (location is the PRIMARY, hard, server-side gate):
  1. LOCATION  pull ONLY the target cities via Workday's location facet
               (server-side; includes multi-location jobs tagged to the city,
               which a text match on "2 Locations" would miss)
  2. DATE      keep last N days from `postedOn` (newest-first, early-stop)
  3. DEDUPE    by job id
  4. INCREMENTAL  skip jobs already in the DB (only new ones are enriched)
  5. GUARD     drop junk/senior titles (cheap)
  6. ENRICH    full description for survivors
  7. RELEVANCE strong AI/Python signal in the description
  8. STORE

Never touches run.py or title_filter.py.
"""
import sys

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import config
from title_filter import REJECT_KEYWORDS, SENIORITY_RE, _contains_any
from store import get_collection, upsert_one, _dedupe_key
from pool import run_pool
from sources import workday_source

# Strong, role-specific signals only (weak boilerplate terms excluded — see notes
# in git history; title_filter.py stays untouched).
DESC_SIGNALS = [
    "machine learning", "deep learning", "pytorch", "tensorflow",
    "scikit-learn", "scikit learn", "keras", "langchain", "llamaindex",
    "hugging face", "huggingface", "large language model", "llm",
    "mlops", "ml engineer", "ai engineer", "computer vision",
    "prompt engineering", "neural network", "rag pipeline",
    "retrieval augmented", "vector database", "fine-tuning", "fine tuning",
    "transformer model", "python developer", "python engineer",
]

# Location is the PRIMARY filter. Cities come from config.SEARCH_LOCATIONS plus
# the Bengaluru alias for Bangalore.
TARGET_CITIES = sorted(set(
    [c.strip().lower() for c in getattr(config, "SEARCH_LOCATIONS", ["Chennai", "Bangalore"])]
    + ["bengaluru", "bangalore"]
))

MAX_AGE_DAYS = int(getattr(config, "CAREER_MAX_AGE_DAYS", 7))
WORKERS_DISCOVER = config.WORKERS.get("workday", 3)
WORKERS_ENRICH = config.WORKERS.get("workday_enrich", 4)


def _title_guard(job) -> tuple[bool, str]:
    t = (job.get("title") or "").strip().lower()
    if not t:
        return False, "missing title"
    if _contains_any(t, REJECT_KEYWORDS):
        return False, "title: reject keyword"
    if SENIORITY_RE.search(t):
        return False, "title: senior/lead-level"
    return True, ""


def _desc_match(job) -> tuple[bool, str]:
    text = ((job.get("description") or "") + "  " + (job.get("title") or "")).lower()
    if _contains_any(text, DESC_SIGNALS):
        return True, ""
    return False, "no AI/Python signal in description"


def _city_offices(desc) -> list:
    """Match this tenant's location offices to the target cities; log the pick."""
    locs = workday_source.list_locations(desc)
    sel = workday_source.select_locations(locs, TARGET_CITIES)
    print(f"\n  [{desc['name']}] target cities={TARGET_CITIES} -> {len(sel)} offices matched:")
    for l in sel:
        print(f"    [x] {l['count']:5d}  {(l['descriptor'] or '')[:52]}")
    if not sel:
        print(f"    (!) no offices matched — check city names via --list-locations")
    return sel


def main(argv=None):
    argv = argv or []
    tenants = workday_source.WORKDAY_TENANTS

    if "--list-locations" in argv:
        for desc in tenants:
            _city_offices(desc)
        return
    if "--list-categories" in argv:
        for desc in tenants:
            cats = workday_source.list_categories(desc)
            sel, decisions = workday_source.select_categories(cats, desc.get("categories"))
            print(f"\n  [{desc['name']}] {len(cats)} categories:")
            for c, reason in decisions:
                mark = "[x]" if reason.startswith("SELECTED") else "[ ]"
                print(f"    {mark} {c['count']:5d}  {(c['descriptor'] or '')[:42]:42s}  {reason}")
        return

    max_age = None if "--all-dates" in argv else MAX_AGE_DAYS

    print("=" * 72)
    print(f"JobPull WORKDAY (location-primary)  |  tenants={[t['name'] for t in tenants]}")
    print(f"  cities={TARGET_CITIES}  max_age_days={max_age}  db={config.DB_NAME!r}")
    print("=" * 72)

    # ── 1+2. DISCOVER by LOCATION facet (primary), date-windowed ─────────
    print("\n[1/7] DISCOVER (location-primary, all categories)")
    tasks = []
    for desc in tenants:
        offices = _city_offices(desc)
        if not offices:
            continue
        applied = {"locations": [l["id"] for l in offices]}
        tasks.append((desc, applied, max_age, "Chennai/Bengaluru"))
    raw = run_pool(tasks, workday_source.discover_facets, WORKERS_DISCOVER,
                   label="discover-workday")
    print(f"  discovered {len(raw)} city listings (in date window)")

    # ── 3. DEDUPE ────────────────────────────────────────────────────────
    seen, unique = set(), []
    for j in raw:
        k, _ = _dedupe_key(j)
        if k in seen:
            continue
        seen.add(k)
        unique.append(j)
    print(f"\n[2/7] DEDUPE  {len(raw)} -> {len(unique)} unique")

    client, col = get_collection()
    counts = {"inserted": 0, "updated": 0}
    new = []
    accepted = []
    try:
        # ── 4. INCREMENTAL: skip jobs already in the DB ──────────────────
        ext_ids = [j["external_id"] for j in unique]
        known = set(d["external_id"] for d in
                    col.find({"source": "workday", "external_id": {"$in": ext_ids}},
                             {"external_id": 1}))
        new = [j for j in unique if j["external_id"] not in known]
        print(f"\n[3/7] INCREMENTAL  {len(unique)} unique -> {len(new)} new "
              f"({len(known)} already in DB, skipped)")
        if known:
            from datetime import datetime
            col.update_many({"source": "workday", "external_id": {"$in": list(known)}},
                            {"$set": {"lastSeenAt": datetime.utcnow()}})

        # ── 5. GUARD (title-only reject) ─────────────────────────────────
        candidates, guard_rejected = [], []
        for j in new:
            ok, reason = _title_guard(j)
            if ok:
                candidates.append(j)
            else:
                j["accepted"] = False
                j["rejectionReason"] = reason
                guard_rejected.append(j)
        print(f"\n[4/7] GUARD  {len(new)} new -> {len(candidates)} candidates "
              f"({len(guard_rejected)} dropped: junk/senior title)")

        # ── 6+7. ENRICH + RELEVANCE ──────────────────────────────────────
        print(f"\n[5/7] ENRICH  descriptions for {len(candidates)} candidates")
        enriched = run_pool(candidates, workday_source.enrich, WORKERS_ENRICH,
                            label="enrich-workday")
        desc_rejected = []
        for j in enriched:
            ok, reason = _desc_match(j)
            j["accepted"] = ok
            j["rejectionReason"] = None if ok else reason
            (accepted if ok else desc_rejected).append(j)
        print(f"[6/7] RELEVANCE (description) -> {len(accepted)} accepted, "
              f"{len(desc_rejected)} no-signal")

        # ── 8. STORE ─────────────────────────────────────────────────────
        for j in accepted + desc_rejected + guard_rejected:
            j.pop("_wd_detail", None)
            counts[upsert_one(j, col)] += 1
    finally:
        client.close()

    # ── SUMMARY ──────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("SUMMARY (workday, location-primary)")
    print(f"  city listings={len(raw)}  unique={len(unique)}  new={len(new)}  accepted={len(accepted)}")
    print(f"  stored: inserted={counts['inserted']}  updated={counts['updated']}")
    print(f"  db={config.DB_NAME}  collection={config.JOBS_COLLECTION}")
    if accepted:
        print("\n  ACCEPTED (Chennai/Bengaluru, AI/Python signal):")
        for j in accepted[:30]:
            print(f"    [OK] {j['title'][:44]:44s} | {j.get('date_posted','')[:14]:14s} | {j['location'][:34]}")
    print("=" * 72)


if __name__ == "__main__":
    main(sys.argv[1:])
