"""SSO routes for Google, GitHub, and Facebook OAuth2 login."""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.auth.auth import oauth_authenticate_current_user
from app.auth.oauth_providers import list_providers
from app.services.sso_service import (
    generate_authorize_url,
    handle_sso_callback,
    unlink_provider,
    get_linked_providers,
)

router = APIRouter()

VALID_PROVIDERS = {"google", "github", "facebook"}


def _validate_provider(provider: str):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}. Must be one of: {', '.join(VALID_PROVIDERS)}")


# ---- Discovery ----

@router.get("/auth/sso/providers", tags=["sso"])
def list_configured_providers():
    """List all configured SSO providers."""
    return {"providers": list_providers()}


# ---- Login Flow ----

@router.get("/auth/sso/{provider}/authorize", tags=["sso"])
def sso_authorize(provider: str, request: Request):
    """Redirect user to provider's authorization page for login/registration."""
    _validate_provider(provider)
    try:
        url, state = generate_authorize_url(provider, action="login")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _authorize_redirect(url, state, request)


@router.get("/auth/sso/{provider}/callback", tags=["sso"])
async def sso_callback(
    provider: str,
    code: str = Query(..., min_length=1, max_length=4096),
    state: str = Query(..., min_length=1, max_length=128),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Handle OAuth2 callback from provider. Returns JWT tokens."""
    _validate_provider(provider)
    result = await handle_sso_callback(db, provider, code, state, request)
    response = JSONResponse(result)
    response.delete_cookie("genesis_sso_state", path="/auth/sso")
    return response


# ---- Link Flow (Authenticated) ----

@router.get("/auth/sso/{provider}/link", tags=["sso"])
def sso_link_authorize(
    provider: str,
    request: Request,
    current_user=Depends(oauth_authenticate_current_user),
):
    """Redirect authenticated user to provider to link SSO account."""
    _validate_provider(provider)
    try:
        url, state = generate_authorize_url(provider, action="link", user_id=str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _authorize_redirect(url, state, request)


def _authorize_redirect(url: str, state: str, request: Request):
    response = RedirectResponse(url=url, status_code=302)
    response.set_cookie(
        "genesis_sso_state", state, max_age=600, httponly=True,
        secure=request.url.scheme == "https", samesite="lax", path="/auth/sso",
    )
    return response


@router.get("/auth/sso/{provider}/link/callback", tags=["sso"])
async def sso_link_callback(
    provider: str,
    code: str = Query(..., min_length=1, max_length=4096),
    state: str = Query(..., min_length=1, max_length=128),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Handle OAuth2 callback for linking SSO to existing account."""
    _validate_provider(provider)
    result = await handle_sso_callback(db, provider, code, state, request)
    response = JSONResponse(result)
    response.delete_cookie("genesis_sso_state", path="/auth/sso")
    return response


# ---- Unlink ----

@router.delete("/auth/sso/{provider}/unlink", tags=["sso"])
def sso_unlink(
    provider: str,
    current_user=Depends(oauth_authenticate_current_user),
    db: Session = Depends(get_db),
):
    """Unlink an SSO provider from the authenticated user's account."""
    _validate_provider(provider)
    return unlink_provider(db, str(current_user.id), provider)


# ---- List Linked Providers ----

@router.get("/auth/sso/linked", tags=["sso"])
def list_linked(
    current_user=Depends(oauth_authenticate_current_user),
    db: Session = Depends(get_db),
):
    """List all SSO providers linked to the authenticated user."""
    providers = get_linked_providers(db, str(current_user.id))
    return {"linked_providers": providers}
