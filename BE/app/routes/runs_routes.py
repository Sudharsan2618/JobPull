"""/api/runs — run history + trigger a run now (background)."""
from fastapi import APIRouter

from app.services import db, notify, runner

router = APIRouter(prefix="/api")


@router.get("/runs")
def list_runs(limit: int = 20):
    out = []
    for r in db.runs().find().sort("startedAt", -1).limit(limit):
        r["_id"] = str(r["_id"])
        r.setdefault("status", "done")
        for k in ("startedAt", "finishedAt"):
            if r.get(k):
                r[k] = r[k].isoformat()
        out.append(r)
    return out


def _launch(stage):
    res = runner.launch(stage)
    return ({"started": False, **res} if res.get("error") else {"started": True, **res})


@router.post("/run/boards")
def run_boards():
    """STAGE A — job boards (LinkedIn/Indeed/Naukri) search + title rejection."""
    return _launch("boards")


@router.post("/run/career")
def run_career():
    """STAGE B — career pages (Workday/Greenhouse) location-primary + LLM relevance."""
    return _launch("career")


@router.post("/run/analyze")
def run_analyze():
    """STAGE C — LLM extraction & analysis on newly accepted jobs (powers Analytics)."""
    return _launch("analyze")


@router.get("/notify/status")
def notify_status():
    return {"configured": notify.configured()}
