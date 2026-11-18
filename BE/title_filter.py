"""
Simple title filter ("fizzbizz") — the ONLY filtering in this module.

Rule:
  1. If the title contains any REJECT keyword  -> reject.
  2. Else if it contains (or fuzzily matches) any ACCEPT keyword -> accept.
  3. Else -> reject ("not in accept list").

No company / industry / experience / location logic. Titles only.
Edit the two lists below to tune — nothing else changes.
"""
import re
from difflib import SequenceMatcher
from typing import Tuple

# Titles we WANT — built around the 4 requested search titles + close synonyms.
ACCEPT_KEYWORDS = [
    "ai engineer",
    "gen ai", "genai", "generative ai",
    "artificial intelligence",
    "python developer", "python engineer",
    "machine learning", "ml engineer",
    "llm", "nlp",
    "ai/ml", "ai ml",
    "deep learning",
    "forward deployed",   # Forward Deployed Engineer
]

# Titles we DROP even if an accept keyword fuzzily matches (guards false positives).
REJECT_KEYWORDS = [
    "sales", "marketing", "business development",
    "recruiter", "recruitment", "talent acquisition",
    "trainer", "teacher", "faculty", "tutor", "instructor",
    "intern",
    "hr ", "human resource",
    "accountant", "finance",
    "support engineer", "customer",
]

# Seniority above mid/associate — rejected (candidate targets mid/associate level).
# Word-boundary so 'lead' won't match 'download', 'sr' won't match inside a word.
SENIORITY_RE = re.compile(
    r"\b(senior|sr|lead|principal|staff|architect|director|head|"
    r"vp|vice president|chief|manager|management)\b"
)

_FUZZY_THRESHOLD = 0.88


def _contains_any(text: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if kw in text:
            return True
    return False


def _fuzzy_any(text: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if SequenceMatcher(None, text, kw).ratio() >= _FUZZY_THRESHOLD:
            return True
        for token in text.split():
            if SequenceMatcher(None, token, kw).ratio() >= _FUZZY_THRESHOLD:
                return True
    return False


def evaluate_title(title: str) -> Tuple[bool, str]:
    """Return (accepted, reason)."""
    t = (title or "").strip().lower()
    if not t:
        return False, "missing title"

    if _contains_any(t, REJECT_KEYWORDS):
        return False, "matched reject keyword"

    if SENIORITY_RE.search(t):
        return False, "senior/lead-level title (targeting mid/associate)"

    if _contains_any(t, ACCEPT_KEYWORDS):
        return True, ""

    if _fuzzy_any(t, ACCEPT_KEYWORDS):
        return True, "fuzzy accept"

    return False, "not in accept list"


# ===========================================================================
# IT-FRESHER profile
# ---------------------------------------------------------------------------
# A second, independent title filter for entry-level roles across ALL of IT:
# freshers, interns, trainees, graduate-engineer-trainees, junior/associate
# developers, plus adjacent functions (QA, support, data, HR). It DELIBERATELY
# inverts the GenAI profile: there, "intern"/"trainee"/"hr" are rejects; here
# they are the whole point. Senior titles and clearly non-IT / blue-collar
# fresher roles (nursing, driving, core-mechanical, field sales) are dropped.
# ===========================================================================

# Strong, unambiguous entry-level signals. If present, the title is accepted
# even when a seniority word also appears (e.g. "Management Trainee").
STRONG_ENTRY = [
    "fresher", "freshers",
    "intern", "internship",
    "trainee", "traineeship",
    "graduate", "campus",
    "apprentice", "apprenticeship",
    "entry level", "entry-level",
]

# Softer entry signals (accepted only when no seniority word is present).
FRESHER_ACCEPT_KEYWORDS = STRONG_ENTRY + [
    "junior", "jr ",
    "associate engineer", "associate software", "associate developer",
    "associate analyst", "associate consultant",
    "management trainee", "mgmt trainee",
    "graduate engineer", "graduate trainee",
    "0-1 year", "0-2 year", "1-2 year",
]

# Abbreviations for Graduate (Engineer) Trainee — word-boundary matched.
FRESHER_ACCEPT_RE = re.compile(r"\b(get|gte|gat)\b")

# Non-IT / blue-collar fresher roles we never want in the IT feed.
FRESHER_REJECT_KEYWORDS = [
    "nurse", "nursing", "pharmacist", "ward boy",
    "driver", "delivery", "rider", "courier",
    "electrician", "welder", "fitter", "machinist", "turner", "lineman",
    "mechanical engineer", "civil engineer", "production engineer",
    "field sales", "field executive", "telecaller", "telecalling", "bpo voice",
    "security guard", "housekeeping", "nanny", "cook", "chef", "waiter",
]


# IT / office role signals — a fresher title must look like an IT-sector role
# (dev, data, QA, support, HR, admin, etc.), so "Junior Clinical Scientist" or
# "Trainee Accountant" don't leak into the IT-fresher feed just for "junior".
_IT_ROLE_SUBSTR = [
    "develop", "software", "engineer", "programmer", "coder",
    "analyst", "analytics", "data ", "database", "dataengineer",
    "test", "quality assur", "automation", "devops", "cloud",
    "web", "frontend", "front end", "front-end", "backend", "back end", "back-end",
    "full stack", "fullstack", "designer",
    "javascript", "python", "java ", "react", "angular", "node", "dotnet", ".net", "php", "golang",
    "information technology", "technical", "technology",
    "human resource", "recruit", "talent", "people operations",
    "support", "helpdesk", "help desk", "service desk",
    "network", "security", "cyber", "system", "sysadmin", "administrator",
    "machine learning", "salesforce", "consultant", "project",
]
_IT_ROLE_RE = re.compile(r"\b(it|ites|hr|qa|qe|sde|sdet|ml|ai|nlp|ui|ux|bi|dba|sql|sap|erp|sre|aws|azure|gcp|devops)\b")


def _is_it_role(t: str) -> bool:
    return _contains_any(t, _IT_ROLE_SUBSTR) or bool(_IT_ROLE_RE.search(t))


def evaluate_fresher(title: str) -> Tuple[bool, str]:
    """IT-fresher profile: (accepted, reason). Independent of evaluate_title."""
    t = (title or "").strip().lower()
    if not t:
        return False, "missing title"

    # 1. Non-IT / blue-collar roles are always out.
    if _contains_any(t, FRESHER_REJECT_KEYWORDS):
        return False, "non-IT / blue-collar role"

    # 2. Strong entry signals override seniority wording ("Management Trainee").
    strong = _contains_any(t, STRONG_ENTRY) or bool(FRESHER_ACCEPT_RE.search(t))

    # 3. A senior/lead/principal/manager title with no strong entry signal is out.
    if SENIORITY_RE.search(t) and not strong:
        return False, "senior/lead-level title"

    # 4. Needs an entry-level indicator...
    if not (strong or _contains_any(t, FRESHER_ACCEPT_KEYWORDS)):
        return False, "no fresher / entry-level indicator"

    # 5. ...AND must read as an IT / office role (not nursing, clinical, etc.).
    if not _is_it_role(t):
        return False, "not an IT / office role"

    return True, ""


# Profile dispatcher — lets the pipeline / API pick a filter by name.
PROFILES = ("genai", "fresher")


def evaluate(title: str, profile: str = "genai") -> Tuple[bool, str]:
    """Dispatch to the right title filter for the given profile."""
    if profile == "fresher":
        return evaluate_fresher(title)
    return evaluate_title(title)


def profiles_for(title: str) -> list:
    """Profiles whose filter ACCEPTS this title — stored on each job as
    `profiles` so the API can serve a user only their chosen track's jobs."""
    out = []
    if evaluate_title(title)[0]:
        out.append("genai")
    if evaluate_fresher(title)[0]:
        out.append("fresher")
    return out
