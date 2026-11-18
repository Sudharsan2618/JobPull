"""
Experience filter — reject jobs whose MINIMUM required experience exceeds the
cap (default 3 years). Applied at two points by design, because experience is
known at different stages per source:

  * Naukri  — experience is in the listing  -> filtered PRE-LLM (run.py),
              so rejected jobs skip both Firecrawl enrichment and the LLM.
  * Indeed  — no listing experience         -> filtered POST-LLM (analyze.py)
  * LinkedIn— no listing experience         -> filtered POST-LLM (analyze.py)

Rule: min required years > cap  -> reject. min <= cap OR unknown -> keep.
So "0-2", "2-5", "3-5", "3+" pass; "4-9", "5+", "6-10" are rejected.
"""
import re

MAX_MIN_EXPERIENCE = 3


def min_years(exp: str):
    """Minimum required years from an experience string, or None if not stated.
    Takes the first number: '3-5 Yrs'->3, '5+ years'->5, '6 to 12 years'->6."""
    if not exp:
        return None
    nums = re.findall(r"\d+", exp)
    return int(nums[0]) if nums else None


def evaluate_experience(exp: str):
    """Return (accepted, reason). Unknown experience is accepted."""
    y = min_years(exp)
    if y is None:
        return True, ""
    if y > MAX_MIN_EXPERIENCE:
        return False, f"requires >{MAX_MIN_EXPERIENCE} yrs (min {y})"
    return True, ""


def experience_of(job: dict) -> str:
    """Best available experience string for a job.
    Naukri trusts the listing; others trust the LLM-extracted range."""
    analysis_exp = (job.get("analysis") or {}).get("experience_range") or ""
    if job.get("source") == "naukri":
        return job.get("experience") or analysis_exp or ""
    return analysis_exp or job.get("experience") or ""
