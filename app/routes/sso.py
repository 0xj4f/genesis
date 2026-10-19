"""SSO routes for Google, GitHub, and Facebook OAuth2 login."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.auth.auth import oauth_authenticate_current_user
from app.auth.oauth_providers import list_providers
from app.services.sso_service import (
    HANDOFF_TTL_SECONDS,
    STATE_TTL_SECONDS,
    create_login_handoff,
    generate_authorize_url,
    get_linked_providers,
    handle_sso_callback,
    issue_tokens_for_user,
    redeem_login_handoff,
    unlink_provider,
)

router = APIRouter()
settings = get_settings()

VALID_PROVIDERS = {"google", "github", "facebook"}
STATE_COOKIE = "genesis_sso_state"
HANDOFF_COOKIE = "genesis_sso_handoff"
COOKIE_PATH = "/auth/sso"


def _validate_provider(provider: str):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}. Must be one of: {', '.join(VALID_PROVIDERS)}")


def _set_cookie(response, request: Request, name: str, value: str, max_age: int):
    response.set_cookie(
        name, value, max_age=max_age, httponly=True,
        secure=request.url.scheme == "https", samesite="lax", path=COOKIE_PATH,
    )


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
    response = RedirectResponse(url=url, status_code=302)
    _set_cookie(response, request, STATE_COOKIE, state, STATE_TTL_SECONDS)
    return response


@router.get("/auth/sso/{provider}/callback", tags=["sso"])
async def sso_callback(
    provider: str,
    request: Request,
    code: Optional[str] = Query(None, min_length=1, max_length=4096),
    state: Optional[str] = Query(None, min_length=1, max_length=128),
    error: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db),
):
    """Handle the provider's redirect.

    With FRONTEND_URL configured, the browser is sent back to the web app with a
    one-time code (login) or a link confirmation; otherwise JSON is returned.
    """
    return await _complete_sso(provider, code, state, error, request, db)


# ---- Link Flow (Authenticated) ----

@router.post("/auth/sso/{provider}/link", tags=["sso"])
def sso_link_authorize(
    provider: str,
    request: Request,
    current_user=Depends(oauth_authenticate_current_user),
):
    """Start linking a provider to the signed-in account.

    Called by the web app with its bearer token (a plain navigation cannot send
    one). Returns the provider URL for the browser to visit and sets the state
    cookie that the callback checks.
    """
    _validate_provider(provider)
    try:
        url, state = generate_authorize_url(provider, action="link", user_id=str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    response = JSONResponse({"authorization_url": url})
    _set_cookie(response, request, STATE_COOKIE, state, STATE_TTL_SECONDS)
    return response


@router.get("/auth/sso/{provider}/link/callback", tags=["sso"])
async def sso_link_callback(
    provider: str,
    request: Request,
    code: Optional[str] = Query(None, min_length=1, max_length=4096),
    state: Optional[str] = Query(None, min_length=1, max_length=128),
    error: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db),
):
    """Alias of the callback; the action (login or link) comes from server-side state."""
    return await _complete_sso(provider, code, state, error, request, db)


# ---- Hand-off to the web app ----

class HandoffExchange(BaseModel):
    code: str = Field(min_length=16, max_length=128)


@router.post("/auth/sso/exchange", tags=["sso"])
def sso_exchange(body: HandoffExchange, request: Request):
    """Trade the one-time code from the callback redirect for tokens.

    Works once, within two minutes, and only in the browser that completed the
    provider sign-in (HttpOnly binding cookie; send with credentials).
    """
    tokens = redeem_login_handoff(body.code, request.cookies.get(HANDOFF_COOKIE))
    response = JSONResponse(tokens)
    response.delete_cookie(HANDOFF_COOKIE, path=COOKIE_PATH)
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


# ---- Helpers ----

def _error_code(exc: HTTPException) -> str:
    """Stable codes the web app turns into messages (no internal details)."""
    detail = str(exc.detail)
    if exc.status_code == 409:
        return "already_linked" if "different user" in detail else "account_exists"
    if exc.status_code == 403:
        return "account_disabled"
    if detail == "provider_denied":
        return "provider_denied"
    if exc.status_code in (502, 503):
        return "provider_error"
    if exc.status_code == 400:
        return "invalid_request"
    return "sso_failed"


async def _complete_sso(provider: str, code, state, error, request: Request, db: Session):
    frontend = settings.frontend_url
    try:
        _validate_provider(provider)
        if error:
            # The user cancelled or the provider refused.
            raise HTTPException(status_code=400, detail="provider_denied")
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or state")
        result = await handle_sso_callback(db, provider, code, state, request)
        linked_user_id = result.pop("user_id", None)
        if frontend and linked_user_id:
            # The web app keeps tokens in memory, which the round trip to the
            # provider cleared; hand it a session for the user who linked.
            result = {**await run_in_threadpool(issue_tokens_for_user, db, linked_user_id, provider, request), "linked": provider}
    except HTTPException as exc:
        if not frontend:
            raise
        response = RedirectResponse(f"{frontend}/sso/callback#error={_error_code(exc)}", status_code=302)
        response.delete_cookie(STATE_COOKIE, path=COOKIE_PATH)
        return response

    if not frontend:
        response = JSONResponse(result)
    else:
        linked = result.pop("linked", None)
        handoff_code, binding = create_login_handoff(result)
        fragment = f"code={handoff_code}" + (f"&linked={linked}" if linked else "")
        response = RedirectResponse(f"{frontend}/sso/callback#{fragment}", status_code=302)
        _set_cookie(response, request, HANDOFF_COOKIE, binding, HANDOFF_TTL_SECONDS)
    response.delete_cookie(STATE_COOKIE, path=COOKIE_PATH)
    return response
