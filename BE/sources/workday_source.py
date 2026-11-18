"""
Workday connector — pulls jobs from Workday's public CXS JSON API.

NO scraping. Every Workday career site (*.myworkdayjobs.com) exposes the same
JSON API. The only per-company facts are (host, tenant, site), which are
DISCOVERED and VERIFIED once (load the company's careers page, follow the link
to *.myworkdayjobs.com, read the /wday/cxs/{tenant}/{site}/ path) — never
guessed from the company name.

Validated live against Genpact:
  host   = genpact.wd108.myworkdayjobs.com
  tenant = genpact
  site   = External_Careers
  list   POST https://{host}/wday/cxs/{tenant}/{site}/jobs
  detail GET  https://{host}/wday/cxs/{tenant}/{site}{externalPath}

RECALL: Workday `searchText` is an unreliable filter (fuzzy — "Artificial
Intelligence" matched Genpact's whole catalog; real GenAI roles were missed by
"AI Engineer"). So the primary path is discover_by_category(): pull whole
job CATEGORIES (jobFamilyGroup facet) with NO keyword, which is deterministic
and complete. Category names differ per company, so we read each tenant's own
category list and pick the relevant ones by NAME keyword (logged, overridable).

DATE: Workday exposes no date facet. Listings carry a relative `postedOn`
("Posted Today" / "Posted 4 Days Ago" / "Posted 30+ Days Ago") and are sorted
newest-first, so a max-age window is applied from postedOn with early-stop.

Public API mirrors run_career: discover*(task) -> [listing dicts], enrich(job).
Standalone — not imported by run.py.
"""
import time
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:  # Loaded in the deployment image; optional for pure imports.
    requests = None

# ── Per-company connector descriptors (DISCOVER + VERIFY once, then add here) ──
# host/tenant/site come from watching the real careers page's network, not guessed.
# Optional "categories": explicit jobFamilyGroup names to pull (case-insensitive,
# substring). If omitted, categories are auto-selected by the keywords below and
# the decision is logged so nothing is silently missed.
WORKDAY_TENANTS: List[Dict[str, Any]] = [
    {"name": "Genpact", "host": "genpact.wd108.myworkdayjobs.com",
     "tenant": "genpact", "site": "External_Careers",
     "categories": ["Technology Solutions and Services", "Data and Analytics"]},
    # {"name": "Capgemini", "host": "...myworkdayjobs.com", "tenant": "...", "site": "...",
    #  "categories": []},  # run: python run_workday.py --list-categories  to see names, then set
]

# Tenant-agnostic category picker (used only when a descriptor has no explicit
# "categories"). INCLUDE catches tech/AI/data/engineering families; EXCLUDE wins
# over INCLUDE to drop obvious non-engineering families and keep cost sane.
# Everything is LOGGED, so review per company and override with "categories".
CATEGORY_INCLUDE = [
    "technolog", "data", "analytic", "engineer", "software", "developer",
    "development", "digital", "product", "cloud", "platform", "architect",
    "machine learning", " ai", "ai ", "ml", "research", "science",
    "information technology", "computer", "applied", "solution",
]
CATEGORY_EXCLUDE = [
    "operations", "finance", "human resource", "legal", "procurement",
    "sales", "marketing", "mobility", "talent", "executive", "risk",
    "communication", "advisory", "intern", "contingent", "supply chain",
    "program management", "infosec", "practice",
]

_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (JobPull career monitor)",
}
_PAGE_LIMIT = 20       # Workday CXS caps page size at 20
_MAX_PAGES = 10        # cap for the legacy searchText discover()
_MAX_PAGES_CAT = 120   # cap for a full category pull (date early-stop usually hits first)
_TIMEOUT = 20


def _cxs_url(desc: Dict[str, Any]) -> str:
    return f"https://{desc['host']}/wday/cxs/{desc['tenant']}/{desc['site']}/jobs"


def _post(desc: Dict[str, Any], applied: Dict[str, Any], search_text: str, offset: int) -> Dict[str, Any]:
    if requests is None:
        raise RuntimeError("requests is not installed")
    body = {"appliedFacets": applied, "limit": _PAGE_LIMIT, "offset": offset, "searchText": search_text}
    r = requests.post(_cxs_url(desc), json=body, headers=_HEADERS, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


# ── Date parsing (Workday has no date facet; parse the relative postedOn) ────
def _days_since_posted(text: str) -> Optional[int]:
    """Approx days since posting from Workday's relative text. None = unknown."""
    t = (text or "").strip().lower()
    if not t:
        return None
    if "today" in t or "just posted" in t or "hour" in t:
        return 0
    if "yesterday" in t:
        return 1
    m = re.search(r"(\d+)\s*\+?\s*day", t)      # "4 days ago", "30+ days ago"
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*\+?\s*month", t)     # "1 month ago"
    if m:
        return int(m.group(1)) * 30
    m = re.search(r"(\d+)\s*\+?\s*week", t)
    if m:
        return int(m.group(1)) * 7
    return None  # unrecognized -> treat as in-window (never silently lose)


def _normalize(posting: Dict[str, Any], desc: Dict[str, Any]) -> Dict[str, Any]:
    external_path = posting.get("externalPath", "")
    req_id = (posting.get("bulletFields") or [""])[0]
    human_url = f"https://{desc['host']}/{desc['site']}{external_path}"
    posted = (posting.get("postedOn") or "").strip()
    return {
        "source": "workday",
        "title": (posting.get("title") or "").strip(),
        "company": desc["name"],
        "location": (posting.get("locationsText") or "").strip(),
        "date_posted": posted,
        "date_posted_days": _days_since_posted(posted),
        "job_url": human_url,
        "apply_url": human_url,
        "company_url": f"https://{desc['host']}/{desc['site']}",
        "description": "",
        "salary": {"raw": ""},
        "job_type": "",
        "skills": [],
        "experience": "",
        "role_summary": "",
        "external_id": f"wd-{desc['tenant']}-{req_id}" if req_id else
                       f"wd-{desc['tenant']}-{hashlib.sha1(human_url.encode('utf-8')).hexdigest()[:12]}",
        "search_title": "workday_monitor",
        "search_location": "workday_monitor",
        "ats": "workday",
        "career_url": f"https://{desc['host']}/{desc['site']}",
        "department": "",
        "requisition_id": req_id,
        # keep the CXS detail path so enrich() can fetch the full description
        "_wd_detail": f"https://{desc['host']}/wday/cxs/{desc['tenant']}/{desc['site']}{external_path}",
    }


# ── Category discovery (per-tenant; names differ per company) ────────────────
def list_categories(desc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return this tenant's jobFamilyGroup categories: [{descriptor, id, count}]."""
    data = _post(desc, {}, "", 0)
    for f in data.get("facets", []):
        if f.get("facetParameter") == "jobFamilyGroup":
            return [{"descriptor": v.get("descriptor"), "id": v.get("id"),
                     "count": v.get("count", 0)} for v in f.get("values", [])]
    return []


def select_categories(cats: List[Dict[str, Any]],
                      explicit: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], List[Tuple[Dict[str, Any], str]]]:
    """
    Choose relevant categories. Returns (selected, decisions) where decisions is
    [(category, reason)] for logging EVERY category (selected or skipped) so a
    right category is never silently dropped.
    """
    selected, decisions = [], []
    for c in cats:
        name = (c.get("descriptor") or "")
        low = name.lower()
        if explicit:
            if any(e.lower() in low for e in explicit):
                selected.append(c); decisions.append((c, "SELECTED (explicit)"))
            else:
                decisions.append((c, "skipped (not in explicit list)"))
            continue
        exc = next((k for k in CATEGORY_EXCLUDE if k in low), None)
        inc = next((k for k in CATEGORY_INCLUDE if k in low), None)
        if exc:
            decisions.append((c, f"skipped (exclude '{exc}')"))
        elif inc:
            selected.append(c); decisions.append((c, f"SELECTED (include '{inc.strip()}')"))
        else:
            decisions.append((c, "skipped (no include match)"))
    return selected, decisions


def list_locations(desc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return this tenant's location facet offices: [{descriptor, id, count}].
    (The 'locations' facet is nested under a 'locationMainGroup' facet.)"""
    data = _post(desc, {}, "", 0)
    for f in data.get("facets", []):
        for v in f.get("values", []):
            if isinstance(v, dict) and v.get("facetParameter") == "locations":
                return [{"descriptor": x.get("descriptor"), "id": x.get("id"),
                         "count": x.get("count", 0)} for x in v.get("values", [])]
    return []


def select_locations(locs: List[Dict[str, Any]], cities: List[str]) -> List[Dict[str, Any]]:
    """Pick every office whose descriptor mentions one of the target cities.
    Matching all offices of a city is what makes multi-location jobs recall-safe."""
    cl = [c.lower() for c in cities]
    return [l for l in locs if any(c in (l.get("descriptor") or "").lower() for c in cl)]


def discover_facets(task: Tuple[Dict[str, Any], Dict[str, Any], Optional[int], str]) -> List[Dict[str, Any]]:
    """
    Task = (descriptor, appliedFacets, max_age_days, label). Generic paginated
    pull for ANY appliedFacets (e.g. {"locations":[...]} or combined with
    {"jobFamilyGroup":[...]}), newest-first with date early-stop.
    """
    desc, applied, max_age_days, label = task
    print(f"[Workday] {desc['name']} / {label} (age<= {max_age_days})")
    out, offset, stop, total = [], 0, False, None
    for _ in range(_MAX_PAGES_CAT):
        try:
            data = _post(desc, applied, "", offset)
        except Exception as e:
            print(f"  [Workday] {desc['name']}/{label} page@{offset} failed: {type(e).__name__}: {e}")
            break
        if total is None:
            total = data.get("total", 0)  # only populated on first page
        postings = data.get("jobPostings") or []
        if not postings:
            break
        for p in postings:
            j = _normalize(p, desc)
            days = j.get("date_posted_days")
            if max_age_days is not None and days is not None and days > max_age_days:
                stop = True
                break
            out.append(j)
        if stop:
            break
        offset += _PAGE_LIMIT
        if total and offset >= total:
            break
        time.sleep(0.3)
    print(f"  [Workday] {desc['name']}/{label} -> {len(out)} in-window listings")
    return out


def discover_by_category(task: Tuple[Dict[str, Any], Dict[str, Any], Optional[int]]) -> List[Dict[str, Any]]:
    """
    Task = (descriptor, category, max_age_days). Pull ALL jobs in one category
    (no keyword), newest-first, stopping once postings fall outside the window.
    max_age_days=None -> no date filter (pull the whole category).
    """
    desc, category, max_age_days = task
    cat_id, cat_name = category["id"], category.get("descriptor", "")
    print(f"[Workday] {desc['name']} / {cat_name} (age<= {max_age_days})")
    out, offset, stop, total = [], 0, False, None
    for _ in range(_MAX_PAGES_CAT):
        try:
            data = _post(desc, {"jobFamilyGroup": [cat_id]}, "", offset)
        except Exception as e:
            print(f"  [Workday] {desc['name']}/{cat_name} page@{offset} failed: {type(e).__name__}: {e}")
            break
        # Workday reports `total` ONLY on the first page (0 afterwards) — capture once.
        if total is None:
            total = data.get("total", 0)
        postings = data.get("jobPostings") or []
        if not postings:
            break
        for p in postings:
            j = _normalize(p, desc)
            days = j.get("date_posted_days")
            if max_age_days is not None and days is not None and days > max_age_days:
                stop = True  # sorted newest-first -> everything after is older
                break
            j["department"] = cat_name
            out.append(j)
        if stop:
            break
        offset += _PAGE_LIMIT
        if total and offset >= total:
            break
        time.sleep(0.3)
    print(f"  [Workday] {desc['name']}/{cat_name} -> {len(out)} in-window listings")
    return out


# ── Legacy searchText discover (kept for reference; low recall — see module doc) ──
def discover(task: Tuple[Dict[str, Any], str]) -> List[Dict[str, Any]]:
    """Task = (descriptor, search_text). Low-recall; prefer discover_by_category."""
    desc, search_text = task
    print(f"[Workday] {desc['name']} <- '{search_text}' (searchText; low recall)")
    out, offset, total = [], 0, None
    for _ in range(_MAX_PAGES):
        try:
            data = _post(desc, {}, search_text, offset)
        except Exception as e:
            print(f"  [Workday] {desc['name']} page@{offset} failed: {type(e).__name__}: {e}")
            break
        if total is None:
            total = data.get("total", 0)  # only populated on first page
        postings = data.get("jobPostings") or []
        if not postings:
            break
        out.extend(_normalize(p, desc) for p in postings)
        offset += _PAGE_LIMIT
        if total and offset >= total:
            break
        time.sleep(0.4)
    print(f"  [Workday] {desc['name']} '{search_text}' -> {len(out)} listings")
    return out


def enrich(job: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch the full description for one Workday job via its CXS detail endpoint."""
    detail_url = job.get("_wd_detail")
    if not detail_url:
        return job
    if requests is None:
        print("[Workday] enrich skipped: requests is not installed")
        return job
    try:
        r = requests.get(detail_url, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        info = (r.json() or {}).get("jobPostingInfo", {})
        job["description"] = (info.get("jobDescription") or "").strip()
        job["date_posted"] = (info.get("startDate") or job.get("date_posted") or "").strip()
        job["job_type"] = (info.get("timeType") or "").strip()
        if info.get("location"):
            job["location"] = info["location"]
    except Exception as e:
        print(f"[Workday] enrich failed for {detail_url}: {type(e).__name__}: {e}")
    return job
