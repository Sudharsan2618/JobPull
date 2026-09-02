"""Unit test for id-based dedupe — no network. Run: python tests/test_dedupe.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from store import _dedupe_key
from sources.naukri_source import _naukri_job_id
from run import _dedupe_by_id

ok = True

# 1. Same LinkedIn job id under different search terms -> same key
a = {"source": "linkedin", "external_id": "li-4458962232",
     "job_url": "https://www.linkedin.com/jobs/view/4458962232", "search_title": "Gen AI Engineer"}
b = {"source": "linkedin", "external_id": "li-4458962232",
     "job_url": "https://www.linkedin.com/jobs/view/4458962232", "search_title": "AI Engineer"}
ka, sa = _dedupe_key(a)
kb, sb = _dedupe_key(b)
print(f"same-id keys equal: {ka == kb} (strategy={sa})")
ok &= (ka == kb and sa == "external_id")

# 2. Different ids -> different keys
c = {"source": "linkedin", "external_id": "li-9999999999", "job_url": "x"}
kc, _ = _dedupe_key(c)
print(f"different-id keys differ: {ka != kc}")
ok &= (ka != kc)

# 3. Naukri id extraction from URL
url = "https://www.naukri.com/job-listings-gen-ai-agentic-ai-engineer-infosys-bengaluru-6-to-10-years-240726032056"
nid = _naukri_job_id(url)
print(f"naukri id extracted: {nid!r}")
ok &= (nid == "nk-240726032056")

# 4. _dedupe_by_id collapses overlap
raw = [a, b, c,
       {"source": "naukri", "external_id": "", "job_url": url},
       {"source": "naukri", "external_id": "", "job_url": url}]  # naukri needs external_id set; here empty -> url fallback
# simulate normalize having set external_id for naukri
raw[3]["external_id"] = nid
raw[4]["external_id"] = nid
unique, collapsed = _dedupe_by_id(raw)
print(f"dedupe_by_id: {len(raw)} -> {len(unique)} unique, {collapsed} collapsed")
ok &= (len(unique) == 3 and collapsed == 2)

print("\nRESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
