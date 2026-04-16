from sqlalchemy.orm import Session
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from uuid import uuid4

from app.auth.auth import authenticate_user, create_access_token, create_refresh_token, decode_token
from app.database.user_db_interface import get_user_by_id_db
from app.services.session_service import (
    create_session,
    validate_refresh_against_session,
    rotate_session_token,
)
from app.models.user_api_model import Token


def get_token_service(db: Session, form_data: OAuth2PasswordRequestForm, request: Request) -> dict:
    user = authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    # Pre-generate the refresh JTI so we can create the session first
    refresh_jti = str(uuid4())

    # Create session bound to this refresh token jti
    session_id = create_session(
        db=db,
        user_id=str(user.id),
        refresh_jti=refresh_jti,
        request=request,
        login_method="password",
    )

    # Build token payload with session ID
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "auth_method": "password",
        "scope": "openid profile email",
        "sid": session_id,
    }

    # Create tokens - both get the sid claim
    access_token, _ = create_access_token(data=payload)
    refresh_token, _ = create_refresh_token(data={**payload, "jti_override": refresh_jti})

    # Update user login tracking
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    user.last_login_method = "password"
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_access_token_service(refresh_token: str, db: Session, request: Request) -> dict:
    payload = decode_token(refresh_token, expected_type="refresh")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    sid = payload.get("sid")

    if not user_id or not jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = get_user_by_id_db(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.disabled or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    # Validate refresh token against session (replay detection)
    if sid:
        validate_refresh_against_session(db, jti, sid)

    # Pre-generate new refresh JTI
    new_refresh_jti = str(uuid4())

    # Rotate session's refresh token jti
    if sid:
        rotate_session_token(db, sid, new_refresh_jti)

    # Build new payload
    new_payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "auth_method": payload.get("auth_method", "password"),
        "scope": payload.get("scope", "openid profile email"),
        "sid": sid,
    }

    new_access_token, _ = create_access_token(data=new_payload)
    new_refresh_token, _ = create_refresh_token(data={**new_payload, "jti_override": new_refresh_jti})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
