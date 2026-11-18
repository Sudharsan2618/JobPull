"""
JobPull — STANDALONE career-page runner (MVP).

  python run_career.py

Deliberately separate from run.py so it NEVER touches the nightly
linkedin/indeed/naukri flow. Same stages, career_page only:

  1. DISCOVER  target companies from config.TARGET_COMPANIES
  2. DEDUPE    by job id
  3. FILTER    shared title filter (your titles only — no widening)
  4. ENRICH    full descriptions via Firecrawl
  5. STORE     streaming upsert into the same DB

It reuses the pipeline helpers (title_filter, store, pool) but is invoked
on its own — `python run.py` remains untouched.
"""
import sys

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import config
from title_filter import evaluate_title
from experience_filter import evaluate_experience
from dedupe_titles import split_duplicates
from store import get_collection, upsert_one, _dedupe_key
from pool import run_pool
from sources import career_source


def _dedupe_by_id(jobs):
    seen = set()
    unique, collapsed = [], 0
    for job in jobs:
        key, _ = _dedupe_key(job)
        if key in seen:
            collapsed += 1
            continue
        seen.add(key)
        unique.append(job)
    return unique, collapsed


def _cap(jobs):
    n = config.MAX_ENRICH_PER_SOURCE
    if n is None:
        return jobs, []
    return jobs[:n], jobs[n:]


def main(argv=None):
    companies = getattr(config, "TARGET_COMPANIES", [])
    workers = config.WORKERS.get("career_page", 1)

    print("=" * 72)
    print(f"JobPull CAREER (standalone)  |  {len(companies)} target companies")
    print(f"  titles={config.SEARCH_TITLES}  workers={workers}  db={config.DB_NAME!r}")
    print("=" * 72)

    # ── STAGE 1: DISCOVER ────────────────────────────────────────────────
    print("\n[1/5] DISCOVER")
    tasks = [(c,) for c in companies]
    raw = run_pool(tasks, career_source.discover, workers, label="discover-career_page")
    print(f"  discovered {len(raw)} raw listings")

    # ── STAGE 2: DEDUPE ──────────────────────────────────────────────────
    unique, collapsed = _dedupe_by_id(raw)
    print(f"\n[2/5] DEDUPE  {len(raw)} -> {len(unique)} unique ({collapsed} collapsed)")

    # ── STAGE 3: FILTER (shared title filter — your titles only) ─────────
    accepted, rejected = [], []
    for job in unique:
        ok, reason = evaluate_title(job.get("title", ""))
        if ok:
            eok, ereason = evaluate_experience(job.get("experience", ""))
            if not eok:
                ok, reason = False, ereason
        job["accepted"] = ok
        job["rejectionReason"] = None if ok else reason
        (accepted if ok else rejected).append(job)
    print(f"\n[3/5] FILTER  {len(unique)} unique -> {len(accepted)} accepted, {len(rejected)} rejected")

    accepted, tc_dups = split_duplicates(accepted)
    for job in tc_dups:
        job["accepted"] = False
        job["rejectionReason"] = "duplicate: same title & company in run"
    rejected += tc_dups
    print(f"       title+company dedupe -> dropped {len(tc_dups)}, {len(accepted)} accepted remain")

    # ── STORE setup ──────────────────────────────────────────────────────
    client, col = get_collection()
    counts = {"inserted": 0, "updated": 0}

    def store_stream(job):
        counts[upsert_one(job, col)] += 1

    try:
        for job in rejected:
            store_stream(job)

        # ── STAGE 4 + 5: ENRICH accepted + streaming STORE ───────────────
        print("\n[4/5] ENRICH (accepted only)  |  [5/5] STORE (streaming)")
        if config.ENRICH_DESCRIPTIONS:
            cp_enrich, cp_rest = _cap(accepted)
            run_pool(cp_enrich, career_source.enrich, workers,
                     on_result=store_stream, label="enrich-career_page")
            for job in cp_rest:
                store_stream(job)
        else:
            for job in accepted:
                store_stream(job)
    finally:
        client.close()

    # ── SUMMARY ──────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("SUMMARY (career_page, standalone)")
    print(f"  discovered={len(raw)}  unique={len(unique)}  accepted={len(accepted)}")
    print(f"  collapsed by job id: {collapsed}")
    print(f"  stored: inserted={counts['inserted']}  updated={counts['updated']}")
    print(f"  db={config.DB_NAME}  collection={config.JOBS_COLLECTION}")
    print("=" * 72)


if __name__ == "__main__":
    main(sys.argv[1:])
