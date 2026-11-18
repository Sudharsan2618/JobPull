"""Shared FastAPI dependencies."""
from fastapi import Depends

from app.auth import require_user
from app.services import users


def current_user(payload: dict = Depends(require_user)) -> dict:
    """Decoded token -> the user record (created on first sight), with `track`."""
    sub = payload.get("sub") or "dev"
    return users.get_or_create(sub, payload.get("email", ""), payload.get("name", ""))
