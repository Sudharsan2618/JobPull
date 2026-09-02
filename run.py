"""
JobPull — optimized pipeline.

  python run.py                 -> all sources (linkedin, indeed, naukri)
  python run.py linkedin naukri -> a subset

Stages:
  1. DISCOVER  (parallel, per-source thread pool)  listings only, no descriptions
  2. DEDUPE    (in-memory)                         collapse by platform job id
  3. FILTER    (titles only)                        drop non-matches before spend
  4. ENRICH    (parallel)                           full descriptions for UNIQUE
                                                    + ACCEPTED jobs only
  5. STORE     (streaming upsert)                   idempotent, writes as it goes

Concurrency = bounded threads per source (config.WORKERS). Firecrawl free plan
= 2 browsers, so Naukri discovery and Naukri enrichment run in SEPARATE stages,
each capped at 2 — never more than 2 Firecrawl browsers at once.
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
from sources import jobspy_source, naukri_source

ALL_SOURCES = ["linkedin", "indeed", "naukri"]


def _dedupe_by_id(jobs):
    """Collapse the same posting seen under different search terms (semantic
    overlap) by platform job id. Keeps first occurrence."""
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


def main(argv):
    sources = [s.lower() for s in argv] or ALL_SOURCES
    unknown = [s for s in sources if s not in ALL_SOURCES]
    if unknown:
        print(f"Unknown source(s): {unknown}. Valid: {ALL_SOURCES}")
        return

    print("=" * 72)
    print(f"JobPull (optimized)  |  titles={config.SEARCH_TITLES}")
    print(f"  locations={config.SEARCH_LOCATIONS}  last {config.HOURS_OLD}h  sources={sources}")
    print(f"  workers={ {s: config.WORKERS[s] for s in sources} }  db={config.DB_NAME!r}")
    print("=" * 72)

    titles, locs = config.SEARCH_TITLES, config.SEARCH_LOCATIONS

    # ── STAGE 1: DISCOVER (parallel per source) ───────────────────────────
    print("\n[1/5] DISCOVER")
    raw = []
    for site in ("linkedin", "indeed"):
        if site in sources:
            tasks = [(site, t, l) for l in locs for t in titles]
            raw += run_pool(tasks, jobspy_source.discover,
                            config.WORKERS[site], label=f"discover-{site}")
    if "naukri" in sources:
        tasks = [(t, l) for l in locs for t in titles]
        raw += run_pool(tasks, naukri_source.discover,
                        config.WORKERS["naukri"], label="discover-naukri")
    print(f"  discovered {len(raw)} raw listings")

    # ── STAGE 2: DEDUPE by job id ─────────────────────────────────────────
    unique, collapsed = _dedupe_by_id(raw)
    print(f"\n[2/5] DEDUPE  {len(raw)} -> {len(unique)} unique "
          f"({collapsed} duplicate postings collapsed by job id)")

    # ── STAGE 3: FILTER (titles only) ─────────────────────────────────────
    accepted, rejected = [], []
    for job in unique:
        ok, reason = evaluate_title(job.get("title", ""))
        # Experience gate — only bites where experience is known pre-LLM (Naukri
        # listing). Indeed/LinkedIn have no listing experience here, so they pass
        # and get judged post-LLM in analyze.py.
        if ok:
            eok, ereason = evaluate_experience(job.get("experience", ""))
            if not eok:
                ok, reason = False, ereason
        job["accepted"] = ok
        job["rejectionReason"] = None if ok else reason
        (accepted if ok else rejected).append(job)
    print(f"\n[3/5] FILTER  {len(unique)} unique -> {len(accepted)} accepted, {len(rejected)} rejected")

    # Collapse mass-posted duplicates (same title+company under different job ids):
    # keep one, mark the rest rejected so they skip enrichment and stay inspectable.
    accepted, tc_dups = split_duplicates(accepted)
    for job in tc_dups:
        job["accepted"] = False
        job["rejectionReason"] = "duplicate: same title & company in run"
    rejected += tc_dups
    print(f"       title+company dedupe -> dropped {len(tc_dups)}, {len(accepted)} accepted remain")

    # ── STORE setup + streaming tally ─────────────────────────────────────
    client, col = get_collection()
    counts = {"inserted": 0, "updated": 0}

    def store_stream(job):
        counts[upsert_one(job, col)] += 1

    try:
        # rejected: store as-is (no enrichment spend)
        for job in rejected:
            store_stream(job)

        # ── STAGE 4 + 5: ENRICH accepted (unique only) + streaming STORE ──
        print(f"\n[4/5] ENRICH (unique+accepted only)  |  [5/5] STORE (streaming)")

        # Indeed: description already in the listing -> store directly.
        for job in (j for j in accepted if j["source"] == "indeed"):
            store_stream(job)

        if config.ENRICH_DESCRIPTIONS:
            li = [j for j in accepted if j["source"] == "linkedin"]
            li_enrich, li_rest = _cap(li)
            run_pool(li_enrich, jobspy_source.enrich_linkedin,
                     config.WORKERS["linkedin"], on_result=store_stream, label="enrich-linkedin")
            for job in li_rest:
                store_stream(job)

            # Naukri enrichment — SEPARATE stage from discovery (Firecrawl 2-cap).
            nk = [j for j in accepted if j["source"] == "naukri"]
            nk_enrich, nk_rest = _cap(nk)
            run_pool(nk_enrich, naukri_source.enrich,
                     config.WORKERS["naukri"], on_result=store_stream, label="enrich-naukri")
            for job in nk_rest:
                store_stream(job)
        else:
            for job in (j for j in accepted if j["source"] != "indeed"):
                store_stream(job)
    finally:
        client.close()

    # ── SUMMARY ───────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("SUMMARY")
    for src in sources:
        n = sum(1 for j in raw if j["source"] == src)
        u = sum(1 for j in unique if j["source"] == src)
        a = sum(1 for j in accepted if j["source"] == src)
        print(f"  {src:10s}: discovered={n:4d}  unique={u:4d}  accepted={a:4d}")
    print(f"  collapsed by job id: {collapsed}")
    print(f"  stored: inserted={counts['inserted']}  updated={counts['updated']}")
    print(f"  db={config.DB_NAME}  collection={config.JOBS_COLLECTION}")
    print("  view with:  python view.py")
    print("=" * 72)


if __name__ == "__main__":
    main(sys.argv[1:])
