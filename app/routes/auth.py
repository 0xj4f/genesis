from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.auth import (
    AuthProvider,
    authenticate_native_user,
    create_session_tokens,
    find_or_create_oauth_user,
    get_client_context,
    get_current_user,
    register_native_user,
    revoke_session_from_refresh_token,
    rotate_refresh_token,
    write_audit_log,
)
from app.database.session import get_db
from app.models.user_api_model import (
    LoginRequest,
    LogoutRequest,
    OAuthCallbackRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.models.user_db_model import Session as UserSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=dict)
def register_endpoint(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = register_native_user(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password.get_secret_value(),
    )
    return {"user_id": user.id, "message": "registered"}


@router.post("/login", response_model=TokenResponse)
def login_endpoint(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    client_ctx: tuple[str | None, str | None] = Depends(get_client_context),
):
    user, identity = authenticate_native_user(db, payload.username_or_email, payload.password.get_secret_value())
    tokens = create_session_tokens(db, user=user, identity=identity, ip_address=client_ctx[0], user_agent=client_ctx[1])
    write_audit_log(db, actor_user_id=user.id, action="login_native", target_type="session")
    return tokens


@router.post("/oauth/google/callback", response_model=TokenResponse)
def google_callback_endpoint(
    payload: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    client_ctx: tuple[str | None, str | None] = Depends(get_client_context),
):
    user, identity = find_or_create_oauth_user(
        db,
        provider=AuthProvider.google,
        provider_user_id=payload.provider_user_id,
        email=payload.email,
        email_verified=payload.email_verified,
        given_name=payload.given_name,
        family_name=payload.family_name,
        picture_url=payload.picture_url,
    )
    tokens = create_session_tokens(db, user=user, identity=identity, ip_address=client_ctx[0], user_agent=client_ctx[1])
    write_audit_log(db, actor_user_id=user.id, action="login_google", target_type="session")
    return tokens


@router.post("/oauth/facebook/callback", response_model=TokenResponse)
def facebook_callback_endpoint(
    payload: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    client_ctx: tuple[str | None, str | None] = Depends(get_client_context),
):
    user, identity = find_or_create_oauth_user(
        db,
        provider=AuthProvider.facebook,
        provider_user_id=payload.provider_user_id,
        email=payload.email,
        email_verified=payload.email_verified,
        given_name=payload.given_name,
        family_name=payload.family_name,
        picture_url=payload.picture_url,
    )
    tokens = create_session_tokens(db, user=user, identity=identity, ip_address=client_ctx[0], user_agent=client_ctx[1])
    write_audit_log(db, actor_user_id=user.id, action="login_facebook", target_type="session")
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_endpoint(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    client_ctx: tuple[str | None, str | None] = Depends(get_client_context),
):
    return rotate_refresh_token(db, refresh_token=payload.refresh_token, ip_address=client_ctx[0], user_agent=client_ctx[1])


@router.post("/logout", response_model=dict)
def logout_endpoint(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    revoke_session_from_refresh_token(db, refresh_token=payload.refresh_token, reason="logout")
    write_audit_log(db, actor_user_id=current_user.id, action="logout", target_type="session")
    return {"message": "logged_out"}


@router.post("/logout-all", response_model=dict)
def logout_all_endpoint(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db.query(UserSession).filter(UserSession.user_id == current_user.id, UserSession.revoked_at.is_(None)).update(
        {"revoked_at": datetime.utcnow(), "revoked_reason": "logout_all"}, synchronize_session=False
    )
    db.commit()
    write_audit_log(db, actor_user_id=current_user.id, action="logout_all", target_type="session")
    return {"message": "all_sessions_revoked"}
