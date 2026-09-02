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
