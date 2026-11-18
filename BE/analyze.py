"""
Grounded extraction engine (Phase 2) — Google Gemini (direct) + structured output.

  python analyze.py --test          # analyze 2 jobs, print result (verify grounding)
  python analyze.py                 # analyze all ACCEPTED jobs missing analysis
  python analyze.py --all           # re-analyze even ones already done

Anti-hallucination design:
  * CONTACTS (emails / phones / links) are extracted DETERMINISTICALLY by regex
    from the description — the LLM never supplies them, so they cannot be invented.
  * The LLM extracts experience_range, key_topics, and bucketed skills with
    temperature 0 + a strict JSON schema (validated by pydantic).
  * GROUNDING GATE: any topic/skill the model returns that does not literally
    appear in the description (word-boundary match) is DROPPED before storing.
  * Rate-gated + retry on 429 (free models are rate-limited).
"""
import argparse
import json
import random
import re
import sys
import threading
import time
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ValidationError
from pymongo import MongoClient

try:
    import requests
except ImportError:  # Present in the deployment image; optional for pure imports.
    requests = None

import config
from pool import run_pool
from experience_filter import evaluate_experience, experience_of

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

BUCKETS = ["skills_concepts", "frameworks", "methodologies", "cloud",
           "languages", "tools_platforms", "databases"]

BUCKET_DESC = (
    "skills_concepts = techniques/concepts (RAG, fine-tuning, prompting, agents, embeddings, NLP, CV); "
    "frameworks = libraries/frameworks (LangChain, PyTorch, TensorFlow, FastAPI, Django, LlamaIndex); "
    "methodologies = approaches/practices (Agile, MLOps, CI/CD, TDD, microservices); "
    "cloud = cloud platforms & services (AWS, Azure, GCP, SageMaker, Bedrock, Vertex AI); "
    "languages = programming languages (Python, Java, SQL, JavaScript, C++); "
    "tools_platforms = tools/platforms (Docker, Kubernetes, Git, MLflow, Airflow, Kafka); "
    "databases = databases & vector stores (PostgreSQL, MongoDB, Redis, Pinecone, FAISS, Chroma)."
)

# ── Deterministic contact extraction (grounded) ───────────────────────────
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL = re.compile(r"https?://[^\s)\]}<>\"']+")
_PHONE = re.compile(r"(?:\+?91[-\s]?)?[6-9]\d{9}\b")


def extract_contacts(desc: str) -> dict:
    emails = sorted(set(_EMAIL.findall(desc)))
    links = sorted(set(_URL.findall(desc)))
    # phones: strip separators, keep 10-digit Indian mobiles; avoid catching years/pins
    phones = sorted(set(re.sub(r"[-\s]", "", p) for p in _PHONE.findall(desc)))
    # a URL local part can look like an email host — keep emails out of links noise
    links = [l for l in links if "@" not in l]
    return {"emails": emails, "phones": phones, "links": links}


# ── Grounding gate ────────────────────────────────────────────────────────
def _in_text(term: str, desc: str) -> bool:
    term = (term or "").strip()
    if not term:
        return False
    # word-boundary-ish match so "RAG" doesn't match "storage"
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", desc, re.I) is not None


def ground(items, desc: str):
    seen, out = set(), []
    for it in items or []:
        it = str(it).strip()
        key = it.lower()
        if it and key not in seen and _in_text(it, desc):
            seen.add(key)
            out.append(it)
    return out


# ── Structured-output schema + pydantic validation ────────────────────────
class Extract(BaseModel):
    experience_range: str = Field(default="")
    key_topics: list[str] = Field(default_factory=list)
    buckets: dict[str, list[str]] = Field(default_factory=dict)


def _gemini_schema():
    """Gemini responseSchema (OpenAPI-subset: uppercase types, no additionalProperties)."""
    return {
        "type": "OBJECT",
        "properties": {
            "experience_range": {"type": "STRING"},
            "key_topics": {"type": "ARRAY", "items": {"type": "STRING"}},
            "buckets": {
                "type": "OBJECT",
                "properties": {b: {"type": "ARRAY", "items": {"type": "STRING"}} for b in BUCKETS},
                "required": BUCKETS,
            },
        },
        "required": ["experience_range", "key_topics", "buckets"],
    }


SYSTEM = (
    "You extract structured facts from a single job description. STRICT RULES:\n"
    "1. Only include items EXPLICITLY present in the description text. Never infer, "
    "guess, or add anything not written.\n"
    "2. experience_range: the required years of experience exactly as stated (e.g. "
    "'3-5 years'); if not stated, return an empty string.\n"
    "3. key_topics: the specific technical concepts, skills, tools and technologies the "
    "description actually discusses. Use the term as it appears.\n"
    "4. buckets: classify every technical term into exactly these buckets. " + BUCKET_DESC + "\n"
    "5. Do not output contact details, salaries, or company info. Output only the JSON."
)


# ── Rate gate + retry (free model limits) ─────────────────────────────────
class _Gate:
    def __init__(self, rpm):
        self.iv = 60.0 / max(1, rpm)
        self.l = threading.Lock()
        self.n = 0.0

    def wait(self):
        with self.l:
            now = time.monotonic()
            if now < self.n:
                time.sleep(self.n - now)
                now = time.monotonic()
            self.n = now + self.iv


_GATE = _Gate(config.GEMINI_RPM)


def _call_llm(desc: str) -> dict:
    """Call Gemini generateContent with a strict responseSchema. Retries on
    429 (rate) / 503 (overload) / network drops with backoff."""
    if requests is None:
        raise RuntimeError("requests is not installed")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": desc[:24000]}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": _gemini_schema(),
        },
    }
    for attempt in range(config.GEMINI_MAX_RETRIES):
        _GATE.wait()
        try:
            r = requests.post(url, json=payload, timeout=90)
        except Exception as e:
            back = min(60, 4 * (2 ** attempt)) + random.uniform(0, 3)
            print(f"  [llm] connection error ({type(e).__name__}); backing off {back:.0f}s "
                  f"(attempt {attempt + 1}/{config.GEMINI_MAX_RETRIES})")
            time.sleep(back)
            continue
        if r.status_code in (429, 503):
            wait = 6 + attempt * 5 + random.uniform(0, 2)
            print(f"  [llm] HTTP {r.status_code} (rate/overload); backing off {wait:.1f}s")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            print(f"  [llm] HTTP {r.status_code}: {r.text[:200]}")
            time.sleep(3)
            continue
        data = r.json()
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            # blocked / empty candidate — surface and retry
            print(f"  [llm] no content in response: {str(data)[:200]}")
            time.sleep(2)
            continue
        try:
            return json.loads(content)
        except Exception:
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                return json.loads(m.group())
            raise RuntimeError("model did not return JSON")
    raise RuntimeError("Gemini retries exhausted")


def analyze_job(job: dict) -> dict:
    """Full grounded analysis for one job. Returns job with ['analysis'] set."""
    desc = job.get("description") or ""
    contacts = extract_contacts(desc)
    # Let LLM/network failures propagate: run_pool skips the job (no writeback),
    # so it stays unanalyzed and is retried on the next resume run — never stored
    # as a false-empty "done". Only a genuinely valid-but-empty result is stored.
    raw = _call_llm(desc)
    parsed = Extract(**raw)

    buckets = {b: ground(parsed.buckets.get(b, []), desc) for b in BUCKETS}
    exp = re.sub(r"[‒-―]", "-", parsed.experience_range).strip()  # normalize dashes
    exp = re.sub(r"\s+", " ", exp)
    job["analysis"] = {
        "experience_range": exp,
        "key_topics": ground(parsed.key_topics, desc),
        "buckets": buckets,
        "contacts": contacts,
        "model": config.GEMINI_MODEL,
        "analyzedAt": datetime.now(timezone.utc).isoformat(),
    }
    return job


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="analyze 2 jobs and print")
    ap.add_argument("--all", action="store_true", help="re-analyze even if already done")
    args = ap.parse_args(argv)

    if not config.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set in JobPull/.env")
        return

    client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=8000)
    col = client[config.DB_NAME][config.JOBS_COLLECTION]

    q = {"accepted": True, "description": {"$ne": ""}}
    if not args.all:
        q["analysis"] = {"$exists": False}
    targets = list(col.find(q))

    if args.test:
        targets = targets[:2]
        for job in targets:
            print(f"\n=== {job['title']} @ {job['company']} ({job['source']}) ===")
            analyze_job(job)
            print(json.dumps(job["analysis"], indent=2, ensure_ascii=False))
        client.close()
        return

    print(f"Analyzing {len(targets)} accepted jobs with {config.GEMINI_MODEL}")
    done = {"n": 0}
    failures = []

    def record_failure(task, exc):
        failures.append((task, exc))

    def writeback(job):
        # Post-LLM experience gate for Indeed/LinkedIn (their experience is only
        # known now). Flip to rejected if the required minimum exceeds the cap.
        upd = {"analysis": job["analysis"], "updatedAt": datetime.now(timezone.utc)}
        eok, ereason = evaluate_experience(experience_of(job))
        if not eok:
            upd["accepted"] = False
            upd["rejectionReason"] = ereason
        col.update_one({"_id": job["_id"]}, {"$set": upd})
        done["n"] += 1

    run_pool(targets, analyze_job, config.GEMINI_WORKERS,
             on_result=writeback, on_error=record_failure, label="analyze")

    remaining = col.count_documents({"accepted": True, "description": {"$ne": ""},
                                     "analysis": {"$exists": False}})
    print(f"\nAnalyzed & stored {done['n']} jobs. Still pending: {remaining}.")
    if remaining:
        print("  (Gemini free tier = 500 requests/day. Re-run 'py -3.13 analyze.py' "
              "to continue — it resumes automatically.)")
    client.close()
    if failures:
        raise RuntimeError(f"{len(failures)} analysis task(s) failed")


if __name__ == "__main__":
    main(sys.argv[1:])
