"""Admin service: analytics, user management, role assignment."""

import math
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4

from app.auth.auth import authenticate_user, create_access_token, create_refresh_token
from app.database.user_db_interface import (
    get_user_by_id_db,
    get_users_paginated_db,
    get_user_analytics_db,
)
from app.database.profile_db_interface import get_profile_by_user_db
from app.database.oauth_account_db_interface import get_oauth_accounts_by_user_db
from app.database.session_db_interface import get_active_sessions_by_user_db
from app.services.session_service import create_session


def admin_login_service(db: Session, username: str, password: str, request: Request) -> dict:
    """Login specifically for admin users. Rejects non-admin/root."""
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if user.disabled or not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    if user.role not in ("admin", "root"):
        raise HTTPException(status_code=403, detail="Access denied. Admin credentials required.")

    refresh_jti = str(uuid4())
    session_id = create_session(db=db, user_id=str(user.id), refresh_jti=refresh_jti, request=request, login_method="password")

    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "auth_method": "password",
        "scope": "openid profile email",
        "sid": session_id,
        "role": user.role,
    }

    access_token, _ = create_access_token(data=payload)
    refresh_token, _ = create_refresh_token(data={**payload, "jti_override": refresh_jti})

    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    user.last_login_method = "password"
    db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def get_analytics(db: Session) -> dict:
    return get_user_analytics_db(db)


def get_users_paginated(db: Session, page: int = 1, per_page: int = 20, search: str = None) -> dict:
    users, total = get_users_paginated_db(db, page, per_page, search)
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    return {
        "users": users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


def get_user_detail(db: Session, user_id: str) -> dict:
    user = get_user_by_id_db(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = get_profile_by_user_db(db, user_id)
    oauth_accounts = get_oauth_accounts_by_user_db(db, user_id)
    sessions = get_active_sessions_by_user_db(db, user_id)

    profile_data = None
    if profile:
        profile_data = {
            "given_name": profile.given_name,
            "family_name": profile.family_name,
            "nick_name": profile.nick_name,
            "picture": profile.picture,
            "locale": profile.locale,
            "timezone": profile.timezone,
        }

    linked = [
        {
            "provider": a.provider,
            "provider_email": a.provider_email,
            "provider_username": a.provider_username,
            "created_at": a.created_at,
        }
        for a in oauth_accounts
    ]

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "disabled": user.disabled,
        "auth_provider": user.auth_provider,
        "is_native": user.is_native,
        "email_verified": user.email_verified,
        "last_login_at": user.last_login_at,
        "last_login_ip": user.last_login_ip,
        "last_login_method": user.last_login_method,
        "created_at": user.created_at,
        "last_modified": user.last_modified,
        "profile": profile_data,
        "sessions_count": len(sessions),
        "linked_providers": linked,
    }


def update_user_role(db: Session, user_id: str, new_role: str, current_user_role: str) -> dict:
    if new_role not in ("user", "admin", "root"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be: user, admin, root")

    # Only root can assign root
    if new_role == "root" and current_user_role != "root":
        raise HTTPException(status_code=403, detail="Only ROOT can assign ROOT role")

    user = get_user_by_id_db(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = new_role
    db.commit()
    return {"message": f"User role updated to {new_role}"}


def toggle_user_status(db: Session, user_id: str) -> dict:
    user = get_user_by_id_db(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "root":
        raise HTTPException(status_code=403, detail="Cannot disable ROOT user")

    user.disabled = not user.disabled
    user.is_active = not user.disabled
    db.commit()
    status = "disabled" if user.disabled else "enabled"
    return {"message": f"User {status}", "disabled": user.disabled}
