"""Admin service: analytics, user management, role assignment."""

import math
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4

from app.auth.auth import (
    authenticate_user, build_user_claims, create_access_token, create_refresh_token, enforce_email_verified,
)
from app.auth.policy import ROLES, can_assign_role, deny, ensure_can_manage
from app.database.user_db_interface import (
    get_user_by_id_db,
    get_users_paginated_db,
    get_user_analytics_db,
    set_user_password_db,
)
from app.database.session_db_interface import revoke_all_user_sessions_db
from app.utils.audit import security_event
from app.utils.security import hash_password
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
    enforce_email_verified(user)

    refresh_jti = str(uuid4())
    session_id = create_session(db=db, user_id=str(user.id), refresh_jti=refresh_jti, request=request, login_method="password")

    payload = build_user_claims(user, sid=session_id, auth_method="password")

    access_token, _ = create_access_token(data=payload)
    refresh_token, _ = create_refresh_token(data={**payload, "jti_override": refresh_jti})

    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    user.last_login_method = "password"
    db.commit()
    security_event("login_succeeded", user_id=str(user.id), method="admin_password")

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
            "date_of_birth": str(profile.date_of_birth) if profile.date_of_birth else None,
            "mobile_number": profile.mobile_number,
            "phone_verified": profile.phone_verified,
            "address_line1": profile.address_line1,
            "city": profile.city,
            "state": profile.state,
            "zip_code": profile.zip_code,
            "country": profile.country,
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


def update_user_role(db: Session, user_id: str, new_role: str, actor) -> dict:
    if new_role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role. Must be: user, admin, root")

    user = get_user_by_id_db(db, user_id, for_update=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Promoting to or demoting from admin/root is root-only; nobody changes their own role.
    if not can_assign_role(actor, user, new_role):
        deny(actor, "change_role", user_id)
    if user.role != new_role:
        old_role = user.role
        user.role = new_role
        db.commit()
        # Tokens carry the role claim: sign the user out so new tokens show the new role.
        revoke_all_user_sessions_db(db, user_id, reason="role_changed")
        security_event("role_changed", actor=str(actor.id), target=user_id, old=old_role, new=new_role)
    return {"message": f"User role updated to {new_role}"}


def toggle_user_status(db: Session, user_id: str, actor) -> dict:
    from app.models.user_db_model import User
    user = db.query(User).filter(User.id == user_id).with_for_update().populate_existing().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "root":
        raise HTTPException(status_code=403, detail="Cannot disable ROOT user")
    ensure_can_manage(actor, user, "toggle_user_status")

    user.disabled = not user.disabled
    user.is_active = not user.disabled
    db.commit()
    if user.disabled:
        revoke_all_user_sessions_db(db, user_id, reason="disabled")
    status = "disabled" if user.disabled else "enabled"
    security_event("user_" + status, actor=str(actor.id), target=user_id)
    return {"message": f"User {status}", "disabled": user.disabled}


def reset_user_password(db: Session, user_id: str, new_password: str, actor) -> dict:
    """Administrator sets another user's password and signs them out everywhere."""
    if str(actor.id) == user_id:
        raise HTTPException(status_code=400, detail="Use POST /users/me/password to change your own password")
    user = get_user_by_id_db(db, user_id, for_update=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_can_manage(actor, user, "reset_password")
    try:
        password_hash = hash_password(new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    set_user_password_db(db, user, password_hash, reason="admin_password_reset")
    security_event("password_reset_by_admin", actor=str(actor.id), target=user_id)
    return {"message": "Password reset. The user was signed out of all sessions."}
