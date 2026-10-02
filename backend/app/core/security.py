from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Header, HTTPException, status
from app.core.config import settings

ALGORITHM = "HS256"

def create_access_token(user: dict, minutes: int = 480) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "department_id": str(user["department_id"]) if user.get("department_id") else None,
        "exp": now + timedelta(minutes=minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

def decode_token(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        return jwt.decode(authorization[7:], settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    return decode_token(authorization)
