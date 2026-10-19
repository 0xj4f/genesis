from sqlalchemy.orm import Session
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from uuid import uuid4

from app.auth.auth import (
    authenticate_user,
    build_user_claims,
    create_access_token,
    create_refresh_token,
    decode_token,
    enforce_email_verified,
)
from app.database.user_db_interface import get_user_by_id_db
from app.services.session_service import (
    create_session,
    validate_refresh_against_session,
    rotate_session_token,
)
from app.utils.audit import security_event


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
    enforce_email_verified(user)

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

    payload = build_user_claims(user, sid=session_id, auth_method="password")

    # Create tokens - both get the sid claim
    access_token, _ = create_access_token(data=payload)
    refresh_token, _ = create_refresh_token(data={**payload, "jti_override": refresh_jti})

    # Update user login tracking
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    user.last_login_method = "password"
    db.commit()
    security_event("login_succeeded", user_id=str(user.id), method="password")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_access_token_service(
    refresh_token: str,
    db: Session,
    request: Request,
    client_id: str | None = None,
    client_secret: str | None = None,
    via_oauth_client: bool = False,
) -> dict:
    """Rotate a refresh token.

    Refresh tokens issued to an OAuth client carry a `client_id` claim and can
    only be redeemed at /oauth/token by that client (with its secret when it is
    confidential). First-party refresh tokens are redeemed at /refresh_token.
    """
    payload = decode_token(refresh_token, expected_type="refresh")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    sid = payload.get("sid")

    if not user_id or not jti or not sid:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    bound_client_id = payload.get("client_id")
    if via_oauth_client:
        if not bound_client_id:
            raise HTTPException(status_code=400, detail="invalid_grant: refresh token was not issued to an OAuth client")
        if client_id != bound_client_id:
            security_event("refresh_client_mismatch", client_id=client_id)
            raise HTTPException(status_code=400, detail="invalid_grant: refresh token was issued to another client")
        # Imported here to avoid a circular import (oidc_service imports this module).
        from app.services.oidc_service import load_client_for_grant
        load_client_for_grant(db, client_id, client_secret, "refresh_token")
    elif bound_client_id:
        raise HTTPException(status_code=400, detail="This refresh token belongs to an OAuth client; use /oauth/token")

    user = get_user_by_id_db(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.disabled or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    # Validate refresh token against session (replay detection)
    validate_refresh_against_session(db, jti, sid, user_id)

    # Pre-generate new refresh JTI
    new_refresh_jti = str(uuid4())

    # Rotate session's refresh token jti
    rotate_session_token(db, sid, new_refresh_jti, jti, user_id)

    new_payload = build_user_claims(
        user,
        sid=sid,
        auth_method=payload.get("auth_method", "password"),
        scope=payload.get("scope", "openid profile email"),
    )
    if bound_client_id:
        # Keep the client binding and the audiences the client was granted.
        new_payload["client_id"] = bound_client_id
        new_payload["aud"] = payload["aud"]

    new_access_token, _ = create_access_token(data=new_payload)
    new_refresh_token, _ = create_refresh_token(data={**new_payload, "jti_override": new_refresh_jti})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
