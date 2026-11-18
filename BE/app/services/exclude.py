"""
Companies hidden by default: staffing/recruiting agencies (they repost other
companies' jobs — you want the real employer) and junk/aggregator rows.

Curated explicit list + a few SAFE keywords. We deliberately avoid broad words
like "consulting/technologies/solutions/systems" because real employers use them
(e.g. "Tata Consultancy Services"). Pass includeAgencies=1 to see them anyway.
"""
EXCLUDED = {
    "top gen ai jobs", "it industry", "big4", "nan", "",
    "bayone solutions", "hyrezy tech solutions", "huntingcube", "talentgigs",
    "impetus career consultants", "vdart digital", "sourcebae", "kenpath technologies",
    "nucleusteq consulting", "artech l.l.c.", "hirojet", "cs tech ai", "skypoint cloud",
    "weekday ai (yc w21)", "weekday ai", "bandhan technologies", "gofix solutions",
}
_KEYWORDS = ("staffing", "recruiter", "recruitment", "talent acquisition", "manpower", "hiring solutions")


def is_excluded(name) -> bool:
    n = (name or "").strip().lower()
    if n in EXCLUDED:
        return True
    return any(k in n for k in _KEYWORDS)
