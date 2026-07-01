"""
auth.py — JWT + bcrypt authentication utilities
"""
import os
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Header
from typing import Optional

SECRET_KEY  = os.getenv("JWT_SECRET", "change_this_secret_in_production")
ALGORITHM   = "HS256"
TOKEN_EXPIRE_HOURS = 24

# ─────────────────────────────────────────────────────────────────────────────
# Password hashing
# ─────────────────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# ─────────────────────────────────────────────────────────────────────────────
# JWT tokens
# ─────────────────────────────────────────────────────────────────────────────
def create_token(user_id: str, username: str, role: str) -> str:
    payload = {
        "sub":      user_id,
        "username": username,
        "role":     role,
        "exp":      datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

# ─────────────────────────────────────────────────────────────────────────────
# Dependency — extract current user from Authorization header
# ─────────────────────────────────────────────────────────────────────────────
def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated.")
    token = authorization.split(" ", 1)[1]
    return decode_token(token)

def require_role(*roles):
    """Factory — returns a FastAPI dependency that enforces one of the given roles."""
    def _check(user: dict = None, authorization: Optional[str] = Header(default=None)):
        if user is None:
            user = get_current_user(authorization)
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role(s): {', '.join(roles)}"
            )
        return user
    return _check
