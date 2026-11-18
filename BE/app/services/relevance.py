"""
LLM relevance gate — the trustworthy keep/drop decision.

Keyword matching on descriptions is fragile (company taglines say "AI" in every
JD). This asks Gemini a single yes/no: is THIS a hands-on AI/ML/GenAI or Python
engineering role for a mid/associate candidate? It reads the real requirements,
not the tagline. Costs ~nothing (see the cost note): tiny prompt, few calls.

Falls back to the strong-signal keyword check if no GEMINI_API_KEY is set, so the
pipeline never hard-depends on the LLM.
"""
import json
import re
import time

try:
    import requests
except ImportError:
    requests = None

import config

# strong-signal fallback (same list the Workday runner uses)
_SIGNALS = [
    "machine learning", "deep learning", "pytorch", "tensorflow", "scikit",
    "keras", "langchain", "llamaindex", "hugging face", "huggingface",
    "large language model", "llm", "mlops", "ml engineer", "ai engineer",
    "computer vision", "prompt engineering", "neural network", "rag pipeline",
    "retrieval augmented", "vector database", "fine-tuning", "fine tuning",
    "transformer model", "python developer", "python engineer",
]

_SYSTEM = (
    "You are screening job descriptions for a candidate targeting hands-on "
    "AI / ML / Generative-AI Engineer or Python Developer roles at a mid or "
    "associate level (roughly 0-5 years). Decide if THIS posting is a genuine "
    "hands-on engineering role of that kind — not sales, ops, finance, support, "
    "testing, or a senior/lead/manager role, and not a role that only mentions "
    "AI in passing company boilerplate. Reply with JSON only: "
    '{"relevant": true|false, "reason": "<=12 words", "seniority": "junior|mid|senior|lead+"}'
)


def _keyword_fallback(job):
    text = ((job.get("description") or "") + " " + (job.get("title") or "")).lower()
    hit = next((s for s in _SIGNALS if s in text), None)
    return {"relevant": bool(hit), "reason": ("signal: " + hit) if hit else "no strong signal",
            "seniority": "?", "engine": "keyword"}


def judge(job) -> dict:
    """Return {relevant, reason, seniority, engine}. Never raises."""
    if not config.GEMINI_API_KEY or requests is None:
        return _keyword_fallback(job)
    desc = (job.get("description") or "")[:8000]
    prompt = f"TITLE: {job.get('title','')}\nLOCATION: {job.get('location','')}\n\nDESCRIPTION:\n{desc}"
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
    payload = {
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=60)
            if r.status_code in (429, 503):
                time.sleep(5 + attempt * 4)
                continue
            if r.status_code != 200:
                break
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(txt) if txt.strip().startswith("{") else json.loads(re.search(r"\{.*\}", txt, re.S).group())
            return {"relevant": bool(data.get("relevant")), "reason": str(data.get("reason", ""))[:80],
                    "seniority": data.get("seniority", "?"), "engine": config.GEMINI_MODEL}
        except Exception:
            time.sleep(2)
    return _keyword_fallback(job)  # any failure -> safe keyword decision
