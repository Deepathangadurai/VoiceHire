"""Auth adapter. REPLACE get_voice_user with your existing auth dependency if you have one.
It must return the authenticated user's id, role ('recruiter'|'candidate') and, for candidates, their candidate id."""
import jwt
from dataclasses import dataclass
from fastapi import Header, HTTPException
from .config import get_settings


@dataclass(frozen=True)
class VoiceUser:
    user_id: str
    role: str
    candidate_id: str | None


async def get_voice_user(authorization: str = Header(default="")) -> VoiceUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        c = jwt.decode(authorization[7:], get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    role = c.get("role")
    if role not in ("recruiter", "candidate"):
        raise HTTPException(403, "Voice assistant not available for this role")
    cid = c.get("candidate_id") or (str(c["sub"]) if role == "candidate" else None)
    return VoiceUser(str(c["sub"]), role, cid)
