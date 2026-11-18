"""
FastAPI app — wires the routes and serves the console.

  python -m uvicorn app.server:app --port 8000     (from the JobPull folder)
  then open http://localhost:8000

Thin by design: every route just calls a service in app/services. The daily
scheduler starts with the app; the existing serve.py / run.py stay untouched.
"""
import os

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse, JSONResponse

from app.routes import jobs, analytics_routes, companies_routes, runs_routes, users_routes
from app.services import db
from app import scheduler
from app.auth import require_user, ENABLED as AUTH_ENABLED

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

app = FastAPI(title="JobPull Console")

# jobs / analytics / users enforce auth and resolve the user via the
# current_user dependency inside each route; companies / runs just need a token.
_auth = [Depends(require_user)]
app.include_router(jobs.router)
app.include_router(analytics_routes.router)
app.include_router(users_routes.router)
app.include_router(companies_routes.router, dependencies=_auth)
app.include_router(runs_routes.router, dependencies=_auth)


@app.get("/api/config")
def public_config():
    """Unauthenticated: lets the frontend know whether login is required."""
    return {"authRequired": AUTH_ENABLED}


@app.on_event("startup")
def _startup():
    try:
        db.companies()  # warm the connection + indexes
        scheduler.start()
    except Exception as e:
        print(f"[startup] warning: {type(e).__name__}: {e}")


@app.get("/api/health")
def health():
    return {"ok": True, "schedule": scheduler.jobs_info()}


@app.get("/")
def console():
    path = os.path.join(WEB_DIR, "console.html")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse({"error": "web/console.html not found"}, status_code=404)
