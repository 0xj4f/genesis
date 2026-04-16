from sqlalchemy.orm import Session as DBSession
from fastapi import HTTPException, Request
from datetime import datetime, timedelta
from uuid import uuid4

from app.database.session_db_interface import (
    create_session_db,
    get_session_by_id_db,
    get_session_by_jti_db,
    get_active_sessions_by_user_db,
    update_session_jti_db,
    revoke_session_db,
    revoke_all_user_sessions_db,
    count_active_sessions_db,
    get_oldest_active_session_db,
)
from app.config import get_settings
from app.utils.helpers import parse_device_name

settings = get_settings()


def create_session(
    db: DBSession,
    user_id: str,
    refresh_jti: str,
    request: Request,
    login_method: str = "password",
) -> str:
    """Create a new session and enforce concurrent session limits. Returns session_id."""
    # Enforce session limit
    active_count = count_active_sessions_db(db, user_id)
    while active_count >= settings.MAX_CONCURRENT_SESSIONS:
        oldest = get_oldest_active_session_db(db, user_id)
        if oldest:
            revoke_session_db(db, oldest.id, reason="session_limit")
            active_count -= 1
        else:
            break

    session_id = str(uuid4())
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    session_data = {
        "id": session_id,
        "user_id": user_id,
        "refresh_token_jti": refresh_jti,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "device_name": parse_device_name(user_agent),
        "login_method": login_method,
        "is_active": True,
        "expires_at": datetime.utcnow() + timedelta(days=settings.OAUTH_REFRESH_TOKEN_TTL_DAYS),
    }

    create_session_db(db, session_data)
    return session_id


def list_sessions(db: DBSession, user_id: str, current_session_id: str | None = None) -> list[dict]:
    """List all active sessions for a user."""
    sessions = get_active_sessions_by_user_db(db, user_id)
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "ip_address": s.ip_address,
            "device_name": s.device_name,
            "login_method": s.login_method,
            "created_at": s.created_at,
            "last_activity_at": s.last_activity_at,
            "is_current": s.id == current_session_id if current_session_id else False,
        })
    return result


def revoke_session(db: DBSession, session_id: str, user_id: str, reason: str = "user_logout") -> bool:
    """Revoke a specific session. Validates ownership."""
    session = get_session_by_id_db(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session already revoked")
    revoke_session_db(db, session_id, reason)
    return True


def revoke_all_sessions(
    db: DBSession, user_id: str, except_session_id: str | None = None, reason: str = "user_logout"
) -> int:
    """Revoke all sessions for a user except the current one."""
    return revoke_all_user_sessions_db(db, user_id, except_session_id, reason)


def validate_refresh_against_session(db: DBSession, jti: str, sid: str) -> str:
    """Validate a refresh token's jti against its session.

    Returns the session_id if valid.
    Raises HTTP 401 if session is invalid or jti mismatches (replay detection).
    """
    session = get_session_by_id_db(db, sid)

    if not session or not session.is_active:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    if session.refresh_token_jti != jti:
        # Potential token theft - JTI mismatch means a rotated token was replayed
        revoke_session_db(db, sid, reason="token_rotation")
        raise HTTPException(
            status_code=401,
            detail="Refresh token has been rotated. Session revoked for security.",
        )

    return session.id


def rotate_session_token(db: DBSession, session_id: str, new_jti: str) -> None:
    """Update the session's refresh token JTI after rotation."""
    update_session_jti_db(db, session_id, new_jti)
