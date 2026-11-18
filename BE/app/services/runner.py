"""
Background run tracker. Each stage runs in a daemon THREAD (not FastAPI's
request threadpool, which long scrapes would starve). A `runs` doc is written
immediately with status='running' and updated to 'done'/'error' on completion,
so the UI can poll /api/runs and show live progress.
"""
import threading
from datetime import datetime, timezone

from app.services import db

# guard so the same stage can't be double-launched while already running
_active = set()
_lock = threading.Lock()


def _start(scope, stage):
    doc = {"status": "running", "stage": stage, "startedAt": datetime.now(timezone.utc),
           "scope": scope, "discovered": 0, "new": 0, "matched": 0, "byCompany": {}, "errors": []}
    return db.runs().insert_one(doc).inserted_id


def _finish(run_id, fields):
    fields = dict(fields)
    fields.setdefault("status", "done")
    fields["finishedAt"] = datetime.now(timezone.utc)
    db.runs().update_one({"_id": run_id}, {"$set": fields})


def is_running(stage):
    with _lock:
        return stage in _active


def launch(stage):
    """Start a stage in the background. Returns {run_id} or {error} if already running."""
    with _lock:
        if stage in _active:
            return {"error": f"{stage} is already running"}
        _active.add(stage)

    scope = {"boards": ["boards: linkedin, indeed, naukri"],
             "career": ["career: workday, greenhouse"],
             "analyze": ["analyze (LLM)"]}.get(stage, [stage])
    run_id = _start(scope, stage)

    def _work():
        from app.services import pipeline
        try:
            if stage == "boards":
                c = pipeline.run_boards()
            elif stage == "career":
                c = pipeline.run_career_counts()
            elif stage == "analyze":
                c = pipeline.run_analyze()
            else:
                c = {"errors": [f"unknown stage {stage}"]}
            c["status"] = "error" if c.get("errors") else "done"
            _finish(run_id, c)
        except Exception as e:
            _finish(run_id, {"status": "error", "errors": [f"{type(e).__name__}: {e}"]})
        finally:
            with _lock:
                _active.discard(stage)

    threading.Thread(target=_work, daemon=True, name=f"run-{stage}").start()
    return {"run_id": str(run_id), "stage": stage}
