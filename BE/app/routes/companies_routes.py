"""/api/companies — the connector registry: list, detect, add, verify, remove."""
from fastapi import APIRouter, Body

from app.services import companies as registry

router = APIRouter(prefix="/api")


@router.get("/companies")
def list_companies():
    registry.seed_defaults()
    return registry.list_all()


@router.post("/companies/detect")
def detect_company(payload: dict = Body(...)):
    """Wizard step: {url, name?} -> detected connector + live sample."""
    return registry.detect_and_verify(payload.get("url", ""), payload.get("name", ""))


@router.post("/companies")
def add_company(payload: dict = Body(...)):
    """Save/update a connector descriptor coming from the wizard."""
    payload.setdefault("enabled", True)
    return registry.upsert(payload)


@router.post("/companies/{name}/verify")
def verify_company(name: str):
    return registry.verify_existing(name)


@router.delete("/companies/{name}")
def delete_company(name: str):
    return {"removed": registry.remove(name)}
