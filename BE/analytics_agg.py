"""
Canonicalized analytics aggregation (Layer 0 + feeds Layer 1/2).

Counts UNIQUE JOBS per canonical skill (a job counts once for RAG no matter how
many surface forms it used), pins each skill to one bucket, and produces:
  - market: skills ranked by how many jobs need them, with % of the analyzed set
  - buckets: per-bucket ranked lists (single-bucket, deduped)
  - denom: number of analyzed jobs the percentages are out of
"""
from collections import defaultdict, Counter

from skills_canon import canonical, BUCKET_OF, BUCKETS


def aggregate(jobs: list) -> dict:
    denom = len(jobs)
    skill_jobs = defaultdict(set)             # canonical -> {job_id}
    bucket_votes = defaultdict(Counter)       # canonical -> Counter(bucket)

    for j in jobs:
        a = j.get("analysis") or {}
        jid = str(j.get("_id"))
        for b in BUCKETS:
            for term in a.get("buckets", {}).get(b, []):
                c = canonical(term)
                if not c:
                    continue
                skill_jobs[c].add(jid)
                bucket_votes[c][b] += 1
        for term in a.get("key_topics", []):   # broadest signal; no bucket
            c = canonical(term)
            if c:
                skill_jobs[c].add(jid)

    def resolve_bucket(c: str) -> str:
        if c in BUCKET_OF:
            return BUCKET_OF[c]
        v = bucket_votes.get(c)
        return v.most_common(1)[0][0] if v else "skills_concepts"

    market = sorted(((c, len(v)) for c, v in skill_jobs.items()), key=lambda x: -x[1])
    buckets = {b: [] for b in BUCKETS}
    for c, jids in skill_jobs.items():
        buckets[resolve_bucket(c)].append((c, len(jids)))
    for b in buckets:
        buckets[b].sort(key=lambda x: -x[1])

    return {
        "denom": denom,
        "market": [(c, n, round(100 * n / denom) if denom else 0) for c, n in market],
        "buckets": buckets,
    }
