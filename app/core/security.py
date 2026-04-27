import secrets
import bcrypt
from fastapi import HTTPException, Request

from app.utils.db import get_session_with_user_by_token


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8")[:72],
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def validate_password_strength(password: str) -> None:
    if len(password or "") < 8:
        raise HTTPException(
            status_code=400,
            detail="La contrasenya ha de tenir com a mínim 8 caràcters",
        )


async def get_current_user(request: Request):
    session_token = request.cookies.get("session_id")
    if not session_token:
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(status_code=307, detail="Redirect")
        raise HTTPException(status_code=401, detail="Sessió caducada")

    row = await get_session_with_user_by_token(session_token)
    if not row:
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(status_code=307, detail="Redirect")
        raise HTTPException(status_code=401, detail="Sessió invàlida")

    if not int(row["is_active"]):
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(status_code=307, detail="Redirect")
        raise HTTPException(status_code=401, detail="Usuari desactivat")

    return {
        "id": row["user_id"],
        "username": row["username"],
        "is_active": bool(row["is_active"]),
        "session_id": row["session_id"],
    }
