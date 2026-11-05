"""Admin service: analytics, user management, role assignment."""

import math
import secrets
from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
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
from app.database.account_request_db_interface import close_requests_db, get_open_request_db
from app.models.account_request_db_model import PASSWORD_RESET
from app.models.user_api_model import validate_password_strength
from app.models.user_db_model import User
from app.database.session_db_interface import revoke_all_user_sessions_db
from app.utils.audit import security_event
from app.utils.security import hash_password
from app.database.profile_db_interface import get_profile_by_user_db
from app.database.oauth_account_db_interface import get_oauth_accounts_by_user_db
from app.database.session_db_interface import count_active_sessions_by_user_db
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


def get_users_paginated(db: Session, page: int = 1, per_page: int = 20, search: str = None,
                        **filters) -> dict:
    users, total = get_users_paginated_db(db, page, per_page, search, **filters)
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
    pending = get_open_request_db(db, user_id, PASSWORD_RESET)

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
        "sessions_count": count_active_sessions_by_user_db(db, user_id),
        "linked_providers": linked,
        "must_change_password": user.must_change_password,
        "password_expires_at": user.password_expires_at,
        "pending_request_id": pending.id if pending else None,
        "pending_password_reset_at": pending.last_requested_at if pending else None,
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
    user = get_user_by_id_db(db, user_id, for_update=True)
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


# No look-alike characters (0/O, 1/l/I) so a password read out or retyped by hand survives.
_TEMPORARY_PASSWORD_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def generate_temporary_password() -> str:
    """Four groups of four (about 92 bits), e.g. Kp7m-Qx3t-Zr9w-Hb2n!, meeting the password policy."""
    while True:
        groups = ("".join(secrets.choice(_TEMPORARY_PASSWORD_ALPHABET) for _ in range(4)) for _ in range(4))
        candidate = "-".join(groups) + "!"
        try:
            return validate_password_strength(candidate)
        except ValueError:
            continue


def issue_password(db: Session, actor, user, new_password: str = None, require_change: bool = True) -> dict:
    """Administrator sets (or generates) another account's password.

    Generated passwords are always temporary: the user must replace them at the
    next sign-in. The user is signed out everywhere, and an open password-reset
    request for them is marked resolved.
    """
    if str(actor.id) == str(user.id):
        raise HTTPException(status_code=400, detail="Use POST /users/me/password to change your own password")
    ensure_can_manage(actor, user, "reset_password")
    generated = new_password is None
    password = generate_temporary_password() if generated else new_password
    temporary = generated or require_change
    try:
        password_hash = hash_password(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    close_requests_db(db, str(user.id), PASSWORD_RESET, "resolved", str(actor.id))
    set_user_password_db(db, user, password_hash, reason="admin_password_reset", temporary=temporary)
    security_event(
        "temporary_password_issued" if temporary else "password_reset_by_admin",
        actor=str(actor.id), target=str(user.id), generated=generated,
    )
    return {
        "message": "Password set. The user was signed out of all sessions.",
        "username": user.username,
        "role": user.role,
        "must_change_password": user.must_change_password,
        "password_expires_at": user.password_expires_at,
        "temporary_password": password if generated else None,
    }


def reset_user_password(db: Session, user_id: str, actor, new_password: str = None, require_change: bool = True) -> dict:
    """Administrator sets another user's password and signs them out everywhere."""
    user = get_user_by_id_db(db, user_id, for_update=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return issue_password(db, actor, user, new_password, require_change)


def create_user_by_admin(db: Session, actor, body) -> dict:
    """Create a password account from the console. Admins create regular users;
    root may also create admins. Nobody creates root accounts here."""
    from app.services.user_service import validate_existing_user

    if body.role != "user" and actor.role != "root":
        deny(actor, "create_user")
    validate_existing_user(db, email=body.email, username=body.username)
    now = datetime.utcnow()
    user = User(
        username=body.username, email=body.email, role=body.role,
        auth_provider="native", is_native=True,
        email_verified=body.email_verified, email_verified_at=now if body.email_verified else None,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered or username already taken")
    security_event("user_created_by_admin", actor=str(actor.id), target=str(user.id), role=body.role)
    password = body.password.get_secret_value() if body.password else None
    result = issue_password(db, actor, user, password, body.require_password_change)
    return {**result, "message": "User created.", "user": user}
