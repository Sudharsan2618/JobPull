"""
Title categorizer — derived from the REAL accepted titles in the DB, not a
guess. Priority order matters (checked top-down; first match wins).

Observed title families (samples):
  Gen AI Engineer / Generative AI / Agentic AI Engineer / Gen AI LLMOps
  Artificial Intelligence Engineer / AI Engineer / AI Developer
  AI/ML Developer / Machine Learning Engineer / AI ML Engineer / AI/ML Architect
  Python Developer / Backend Python Developer / Python AI Developer
  Data Science Gen AI Engineer / Applied AI ML Director - Head of AI & Data Science
"""
import re

# (category, regex) — first match wins.
_RULES = [
    ("Gen AI / Agentic", re.compile(r"\bgen\s*ai\b|generative|agentic|\bllm(ops)?\b|\brag\b", re.I)),
    ("Python Developer", re.compile(r"\bpython\b", re.I)),
    ("AI/ML Engineer",   re.compile(r"\bml\b|machine\s*learning|\bai[\s/-]*ml\b|\bml[\s/-]*ai\b|algorithm", re.I)),
    ("Data Science",     re.compile(r"data\s*scien", re.I)),
    ("AI Engineer",      re.compile(r"artificial\s*intelligence|\bai\b", re.I)),
]

CATEGORIES = [c for c, _ in _RULES] + ["Other"]


def categorize(title: str) -> str:
    t = title or ""
    for cat, rx in _RULES:
        if rx.search(t):
            return cat
    return "Other"
