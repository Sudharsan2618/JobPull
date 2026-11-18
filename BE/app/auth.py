"""
Auth0 access-token validation (RS256 via JWKS).

Enforced only when AUTH0_DOMAIN + AUTH0_AUDIENCE are set in BE/.env; otherwise
the dependency is a no-op (local dev without auth). Routes opt in by depending
on `require_user`, which returns the decoded token payload (sub, email, …).
"""
import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient

import config

ENABLED = bool(config.AUTH0_DOMAIN and config.AUTH0_AUDIENCE)
_ISSUER = f"https://{config.AUTH0_DOMAIN}/" if ENABLED else ""
_jwks = PyJWKClient(f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json") if ENABLED else None


def require_user(request: Request) -> dict:
    """FastAPI dependency: 401 unless a valid Auth0 access token is present."""
    if not ENABLED:
        return {"sub": "dev", "email": "dev@local"}
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth[7:]
    try:
        signing_key = _jwks.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=config.AUTH0_AUDIENCE,
            issuer=_ISSUER,
        )
    except Exception as e:  # invalid signature / audience / issuer / expiry
        raise HTTPException(status_code=401, detail=f"invalid token: {type(e).__name__}")
    return payload
