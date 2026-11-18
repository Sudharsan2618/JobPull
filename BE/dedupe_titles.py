"""
Title+Company de-duplication.

Job-id dedupe (store._dedupe_key) collapses the exact same posting seen under
different search terms. But boards mass-post the SAME role under many distinct
job ids (e.g. Accenture "AI/ML Engineer" reposted across cities). Those share a
title and company but not an id, so id-dedupe keeps them all.

This collapses them by a normalized (title, company) key: keep one, reject the
rest. Applied per-run in the scraper and, retroactively, over the stored data.
"""
import re


def tc_key(title: str, company: str) -> str:
    """Normalized 'title|company' key: lowercased, punctuation flattened."""
    def norm(s):
        s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
        return re.sub(r"\s+", " ", s).strip()
    return f"{norm(title)}|{norm(company)}"


def split_duplicates(jobs, keep=None):
    """
    Split jobs into (unique, duplicates) by tc_key, keeping ONE per key.

    `keep(a, b)` -> the better of two jobs for the same key (returns the one to
    keep). Default keeps the first seen. Both title and company must be present
    for a job to participate; jobs missing either are always kept (never merged).
    """
    if keep is None:
        keep = lambda a, b: a  # first wins
    chosen, dups = {}, []
    passthrough = []
    for j in jobs:
        t, c = (j.get("title") or "").strip(), (j.get("company") or "").strip()
        if not t or not c:
            passthrough.append(j)
            continue
        k = tc_key(t, c)
        if k not in chosen:
            chosen[k] = j
        else:
            winner = keep(chosen[k], j)
            loser = j if winner is chosen[k] else chosen[k]
            chosen[k] = winner
            dups.append(loser)
    return passthrough + list(chosen.values()), dups
