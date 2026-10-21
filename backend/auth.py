"""Login tokens (JWT) and role checks for the API."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import get_user_by_id

ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(hours=int(os.getenv("JWT_EXPIRE_HOURS", "12")))
_SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".jwt_secret")


def _load_secret() -> str:
    """
    Use JWT_SECRET from the environment if set. Otherwise create a random
    secret once and keep it in backend/.jwt_secret so tokens survive restarts.
    """
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret
    if os.path.exists(_SECRET_FILE):
        with open(_SECRET_FILE) as f:
            saved = f.read().strip()
        if saved:
            return saved
    new_secret = secrets.token_urlsafe(64)
    fd = os.open(_SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(new_secret)
    return new_secret


SECRET_KEY = _load_secret()
_bearer = HTTPBearer(auto_error=False)


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _unauthorized(detail: str = "Not authenticated."):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_token(token: Optional[str]) -> dict:
    if not token:
        raise _unauthorized()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized("Session expired or invalid. Please log in again.")
    # Look the user up every time so deleted accounts and role changes take effect at once.
    user = get_user_by_id(user_id)
    if user is None:
        raise _unauthorized("Account no longer exists.")
    return user


def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> dict:
    return _user_from_token(creds.credentials if creds else None)


def get_current_user_header_or_query(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    token: Optional[str] = Query(None),
) -> dict:
    """For plain links (file downloads) that can't send an Authorization header."""
    return _user_from_token(creds.credentials if creds else token)


def require_roles(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="You don't have permission to do this.")
        return user
    return checker


require_admin = require_roles("admin")
require_staff = require_roles("teacher", "admin")
require_teacher = require_roles("teacher")
require_student = require_roles("student")


def ensure_self_or_staff(user: dict, target_user_id: int):
    """Students may only see their own data; teachers and admins may see anyone's."""
    if user["role"] in ("teacher", "admin"):
        return
    if user["id"] != target_user_id:
        raise HTTPException(status_code=403, detail="You can only access your own records.")
