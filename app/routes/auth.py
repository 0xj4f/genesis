from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.auth_service import get_token_service, refresh_access_token_service
from app.services.session_service import list_sessions, revoke_session, revoke_all_sessions
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app.models.user_api_model import Token, UserMinimal
from app.models.session_api_model import SessionResponse, SessionListResponse
from app.auth.auth import oauth_authenticate_internal_service, oauth_authenticate_current_user, decode_token
from app.auth.keys import get_jwks

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ---- Token Endpoints ----

@router.post("/token", tags=["auth"], response_model=Token)
def get_token_endpoint(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return get_token_service(db=db, form_data=form_data, request=request)


@router.post("/token/validate", tags=["auth"], response_model=UserMinimal)
def validate_token(user: UserMinimal = Depends(oauth_authenticate_internal_service)):
    return user


@router.post("/refresh_token", tags=["auth"], response_model=Token)
def refresh_token_endpoint(
    request: Request,
    refresh_token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    return refresh_access_token_service(refresh_token=refresh_token, db=db, request=request)


# ---- JWKS Endpoint ----

@router.get("/.well-known/jwks.json", tags=["auth"])
def jwks_endpoint():
    return get_jwks()


# ---- Session Management Endpoints ----

@router.get("/auth/sessions", tags=["sessions"], response_model=SessionListResponse)
def list_user_sessions(
    request: Request,
    current_user=Depends(oauth_authenticate_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # Extract current session ID from token
    payload = decode_token(token, expected_type="access")
    current_sid = payload.get("sid")

    sessions = list_sessions(db, str(current_user.id), current_session_id=current_sid)
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/auth/sessions/{session_id}", tags=["sessions"])
def revoke_user_session(
    session_id: str,
    current_user=Depends(oauth_authenticate_current_user),
    db: Session = Depends(get_db),
):
    revoke_session(db, session_id, str(current_user.id), reason="user_logout")
    return {"message": "Session revoked"}


@router.delete("/auth/sessions", tags=["sessions"])
def revoke_all_user_sessions(
    current_user=Depends(oauth_authenticate_current_user),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # Keep current session active, revoke all others
    payload = decode_token(token, expected_type="access")
    current_sid = payload.get("sid")

    count = revoke_all_sessions(
        db, str(current_user.id), except_session_id=current_sid, reason="user_logout"
    )
    return {"message": f"Revoked {count} session(s)"}
