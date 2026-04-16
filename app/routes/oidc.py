"""OIDC Provider routes: discovery, authorize, token, userinfo."""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import urlencode

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
)
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

    For first-party apps, consent is auto-approved.
    Returns redirect with authorization code.
    """
    # Validate the request
    validate_authorize_request(
        db, client_id, redirect_uri, response_type, scope,
        code_challenge, code_challenge_method,
    )

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
    params = {"code": code, "state": state}
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        url=f"{redirect_uri}{separator}{urlencode(params)}",
        status_code=302,
    )


# ---- Token Endpoint ----

@router.post("/oauth/token", tags=["oidc"])
async def token_endpoint(
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
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            parts = decoded.split(":", 1)
            if len(parts) == 2:
                client_id = client_id or parts[0]
                client_secret = client_secret or parts[1]

    if grant_type == "authorization_code":
        if not code or not redirect_uri or not client_id:
            raise HTTPException(status_code=400, detail="code, redirect_uri, and client_id are required")
        return exchange_authorization_code(
            db, code, client_id, client_secret, redirect_uri, code_verifier, request,
        )

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token is required")
        return refresh_access_token_service(refresh_token, db, request)

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
    user_id = payload.get("sub")
    scope_str = payload.get("scope", "")
    scopes = scope_str.split()

    if "openid" not in scopes:
        raise HTTPException(status_code=403, detail="Token must have 'openid' scope")

    return get_userinfo(db, user_id, scopes)
