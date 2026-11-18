"""/api/me — the signed-in user's profile + one-time track choice."""
from fastapi import APIRouter, Body, Depends, HTTPException

from app.deps import current_user
from app.services import users

router = APIRouter(prefix="/api")


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return users.public(user)


@router.put("/me/track")
def set_track(payload: dict = Body(...), user: dict = Depends(current_user)):
    track = (payload.get("track") or "").strip()
    try:
        updated = users.set_track(user["sub"], track)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return users.public(updated)
