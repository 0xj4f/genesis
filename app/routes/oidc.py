"""OIDC Provider routes: discovery, authorize, token, userinfo."""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Literal, Optional

from app.database.session import get_db
from app.auth.auth import oauth_authenticate_current_user, decode_token
from app.auth.keys import get_jwks
from app.services.oidc_service import (
    get_openid_configuration,
    validate_authorize_request,
    create_authorization_code,
    exchange_authorization_code,
    handle_client_credentials,
    get_userinfo,
    get_public_client_info,
    authorization_redirect,
)
from app.utils.audit import security_event
from app.services.auth_service import refresh_access_token_service
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


# ---- Discovery ----

@router.get("/.well-known/openid-configuration", tags=["oidc"])
def openid_configuration():
    """OpenID Connect Discovery endpoint."""
    return get_openid_configuration()


# ---- Authorization Endpoint ----

@router.get("/oauth/authorize", tags=["oidc"])
def authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query("openid"),
    state: str = Query(...),
    nonce: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(oauth_authenticate_current_user),
):
    """OIDC Authorization endpoint. Requires authenticated user.

    Only first-party clients are approved without asking. Other clients must go
    through the web app's consent screen (POST /oauth/authorize).
    Returns redirect with authorization code.
    """
    # Validate the request
    validated = validate_authorize_request(
        db, client_id, redirect_uri, response_type, scope,
        code_challenge, code_challenge_method,
    )
    if not validated["client"].is_first_party:
        raise HTTPException(status_code=403, detail="consent_required")

    # Generate authorization code
    code = create_authorization_code(
        db,
        client_id=client_id,
        user_id=str(current_user.id),
        redirect_uri=redirect_uri,
        scope=scope,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    # Redirect back to client with code
    return RedirectResponse(
        url=authorization_redirect(redirect_uri, {"code": code, "state": state}),
        status_code=302,
    )


class AuthorizeDecision(BaseModel):
    response_type: str = Field(max_length=20)
    client_id: str = Field(max_length=64)
    redirect_uri: str = Field(max_length=2048)
    scope: str = Field("openid", max_length=500)
    state: str = Field(min_length=1, max_length=500)
    nonce: Optional[str] = Field(None, max_length=255)
    code_challenge: Optional[str] = Field(None, max_length=128)
    code_challenge_method: Optional[str] = Field(None, max_length=10)
    consent: Literal["approve", "deny"]


@router.post("/oauth/authorize", tags=["oidc"])
def authorize_with_consent(
    decision: AuthorizeDecision,
    db: Session = Depends(get_db),
    current_user=Depends(oauth_authenticate_current_user),
):
    """Called by the web app's consent screen after the user signs in.

    Returns {"redirect_to": ...} for the browser to follow: either the code or
    error=access_denied, both sent only to the client's registered redirect_uri.
    """
    validate_authorize_request(
        db, decision.client_id, decision.redirect_uri, decision.response_type, decision.scope,
        decision.code_challenge, decision.code_challenge_method,
    )
    if decision.consent == "deny":
        security_event("oauth_consent_denied", user_id=str(current_user.id), client_id=decision.client_id)
        return {"redirect_to": authorization_redirect(decision.redirect_uri, {"error": "access_denied", "state": decision.state})}
    code = create_authorization_code(
        db,
        client_id=decision.client_id,
        user_id=str(current_user.id),
        redirect_uri=decision.redirect_uri,
        scope=decision.scope,
        nonce=decision.nonce,
        code_challenge=decision.code_challenge,
        code_challenge_method=decision.code_challenge_method,
    )
    security_event("oauth_consent_granted", user_id=str(current_user.id), client_id=decision.client_id)
    return {"redirect_to": authorization_redirect(decision.redirect_uri, {"code": code, "state": decision.state})}


@router.get("/oauth/clients/{client_id}/public", tags=["oidc"])
def public_client_info(client_id: str, db: Session = Depends(get_db)):
    """Client name and scopes for the consent screen."""
    return get_public_client_info(db, client_id)


# ---- Token Endpoint ----

# A plain def: client authentication and database work run in the threadpool
# instead of blocking the event loop.
@router.post("/oauth/token", tags=["oidc"])
def token_endpoint(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """OIDC Token endpoint. Supports authorization_code, refresh_token, client_credentials."""

    # Try HTTP Basic Auth for client credentials
    if not client_id or not client_secret:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Basic "):
            import base64
            import binascii
            from urllib.parse import unquote_plus
            try:
                decoded = base64.b64decode(auth_header[6:], validate=True).decode("utf-8")
                basic_id, basic_secret = decoded.split(":", 1)
                basic_id, basic_secret = unquote_plus(basic_id), unquote_plus(basic_secret)
                if client_id and client_id != basic_id or client_secret and client_secret != basic_secret:
                    raise ValueError("Conflicting credentials")
                client_id, client_secret = basic_id, basic_secret
            except (ValueError, UnicodeError, binascii.Error):
                raise HTTPException(status_code=401, detail="Invalid client credentials")

    if grant_type == "authorization_code":
        if not code or not redirect_uri or not client_id:
            raise HTTPException(status_code=400, detail="code, redirect_uri, and client_id are required")
        return exchange_authorization_code(
            db, code, client_id, client_secret, redirect_uri, code_verifier, request,
        )

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token is required")
        return refresh_access_token_service(
            refresh_token, db, request,
            client_id=client_id, client_secret=client_secret, via_oauth_client=True,
        )

    elif grant_type == "client_credentials":
        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="client_id and client_secret are required")
        return handle_client_credentials(db, client_id, client_secret, scope)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


# ---- UserInfo Endpoint ----

@router.get("/oauth/userinfo", tags=["oidc"])
def userinfo(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """OIDC UserInfo endpoint. Returns claims based on token scopes."""
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token required")

    payload = decode_token(token, expected_type="access")
    oauth_authenticate_current_user(token, db)
    user_id = payload.get("sub")
    scope_str = payload.get("scope", "")
    scopes = scope_str.split()

    if "openid" not in scopes:
        raise HTTPException(status_code=403, detail="Token must have 'openid' scope")

    return get_userinfo(db, user_id, scopes)
