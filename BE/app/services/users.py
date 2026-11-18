"""User profiles — one doc per Auth0 identity, holding the chosen track.

A user picks their track ONCE at signup ("genai" or "fresher"); every data
request is then served for that track. `track` is None until they choose.
"""
from datetime import datetime, timezone

from app.services import db

VALID_TRACKS = ("genai", "fresher")


def get_or_create(sub: str, email: str = "", name: str = "") -> dict:
    """Fetch the user by Auth0 sub, creating a bare record on first sight."""
    u = db.users().find_one({"sub": sub})
    if u:
        return u
    now = datetime.now(timezone.utc)
    doc = {"sub": sub, "email": email or "", "name": name or "", "track": None,
           "createdAt": now, "updatedAt": now}
    db.users().insert_one(doc)
    return doc


def set_track(sub: str, track: str) -> dict:
    if track not in VALID_TRACKS:
        raise ValueError(f"invalid track: {track!r}")
    now = datetime.now(timezone.utc)
    db.users().update_one(
        {"sub": sub},
        {"$set": {"track": track, "updatedAt": now},
         "$setOnInsert": {"sub": sub, "createdAt": now}},
        upsert=True,
    )
    return db.users().find_one({"sub": sub})


def public(u: dict) -> dict:
    return {
        "sub": u.get("sub"),
        "email": u.get("email", ""),
        "name": u.get("name", ""),
        "track": u.get("track"),
        "onboarded": bool(u.get("track")),
    }
