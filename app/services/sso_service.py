"""SSO service: sign-in with Google, GitHub and Facebook.

The OAuth 2.0 protocol work (authorization URL, PKCE, token exchange, client
authentication) uses Authlib. Google is an OpenID Connect provider, so its signed
ID token is verified (issuer, audience, expiry, nonce) with PyJWT and the
provider's JWKS. GitHub and Facebook are plain OAuth 2.0, so their user APIs are
called with the access token.

Provider access/refresh tokens are used only during the callback and are never
stored.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import httpx
import jwt
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuthError
from authlib.oauth2.rfc6749.parameters import prepare_grant_uri
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.auth import build_user_claims, create_access_token, create_refresh_token
from app.auth.oauth_providers import get_provider, OAuthProviderConfig
from app.config import get_settings
from app.database.oauth_account_db_interface import (
    create_oauth_account_db,
    get_oauth_account_by_provider_db,
    get_oauth_account_by_user_and_provider_db,
)
from app.database.user_db_interface import get_user_by_email_db, get_user_by_username_db
from app.services.session_service import create_session
from app.utils.audit import security_event
from app.utils.security_store import get_security_store, SecurityStoreUnavailable

settings = get_settings()
logger = logging.getLogger(__name__)

STATE_TTL_SECONDS = 600
HANDOFF_TTL_SECONDS = 120

_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _oauth_client(provider: OAuthProviderConfig, token: dict | None = None) -> AsyncOAuth2Client:
    return AsyncOAuth2Client(
        client_id=provider.client_id,
        client_secret=provider.client_secret,
        token_endpoint_auth_method="client_secret_post",
        scope=" ".join(provider.scopes),
        redirect_uri=provider.redirect_uri,
        code_challenge_method="S256" if provider.pkce else None,
        token=token,
        timeout=10.0,
    )


def _store_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Security service temporarily unavailable")


def generate_authorize_url(provider_name: str, action: str = "login", user_id: str | None = None) -> tuple[str, str]:
    """Build the provider's authorization URL. Returns (authorize_url, state).

    The PKCE verifier and OIDC nonce stay server-side with the state; only the
    derived challenge and the nonce travel through the browser.
    """
    provider = get_provider(provider_name)

    state = secrets.token_urlsafe(32)
    code_verifier = generate_token(64) if provider.pkce else None
    nonce = secrets.token_urlsafe(32) if provider.oidc else None
    state_data = {
        "provider": provider_name,
        "action": action,  # "login" or "link"
        "user_id": user_id,  # set when action=link
        "created_at": datetime.utcnow().isoformat(),
        "code_verifier": code_verifier,
        "nonce": nonce,
    }
    try:
        get_security_store().put_state(state, state_data, STATE_TTL_SECONDS)
    except SecurityStoreUnavailable:
        raise _store_unavailable()

    params = {}
    if code_verifier:
        params["code_challenge"] = create_s256_code_challenge(code_verifier)
        params["code_challenge_method"] = "S256"
    if nonce:
        params["nonce"] = nonce
    url = prepare_grant_uri(
        provider.authorize_url,
        client_id=provider.client_id,
        response_type="code",
        redirect_uri=provider.redirect_uri,
        scope=" ".join(provider.scopes),
        state=state,
        **params,
    )
    return url, state


def validate_state(state: str) -> dict:
    """Validate and consume a state parameter. Returns state data or raises."""
    try:
        state_data = get_security_store().pop_state(state)
    except SecurityStoreUnavailable:
        raise _store_unavailable()
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    # Check expiry (10 min)
    created = datetime.fromisoformat(state_data["created_at"])
    if datetime.utcnow() - created > timedelta(seconds=STATE_TTL_SECONDS):
        raise HTTPException(status_code=400, detail="State parameter expired")

    return state_data


async def exchange_code_for_tokens(provider: OAuthProviderConfig, code: str, code_verifier: str | None) -> dict:
    """Exchange the authorization code (with the PKCE verifier) for provider tokens."""
    kwargs = {"code": code}
    if code_verifier:
        kwargs["code_verifier"] = code_verifier
    try:
        async with _oauth_client(provider) as client:
            token = await client.fetch_token(provider.token_url, **kwargs)
    except (OAuthError, httpx.HTTPError, ValueError) as exc:
        # Provider error details are logged, not echoed to the browser.
        logger.warning("Token exchange with %s failed: %s", provider.name, exc)
        raise HTTPException(status_code=502, detail=f"Failed to exchange code with {provider.name}")
    if not token.get("access_token"):
        raise HTTPException(status_code=502, detail="No access token from provider")
    return dict(token)


def verify_id_token(provider: OAuthProviderConfig, id_token: str, nonce: str | None) -> dict:
    """Verify an OIDC ID token's signature and claims against the provider."""
    jwks_client = _jwks_clients.get(provider.jwks_uri)
    if jwks_client is None:
        jwks_client = _jwks_clients.setdefault(
            provider.jwks_uri, jwt.PyJWKClient(provider.jwks_uri, cache_keys=True, lifespan=3600, timeout=10)
        )
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=provider.client_id,
            issuer=provider.issuers,
            options={"require": ["iss", "sub", "aud", "exp", "iat"]},
        )
    except jwt.PyJWTError as exc:
        logger.warning("Rejected ID token from %s: %s", provider.name, exc)
        raise HTTPException(status_code=502, detail="Invalid ID token from provider")
    if not nonce or not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
        logger.warning("Rejected ID token from %s: nonce mismatch", provider.name)
        raise HTTPException(status_code=502, detail="Invalid ID token from provider")
    return claims


async def fetch_identity(provider: OAuthProviderConfig, token: dict, nonce: str | None) -> dict:
    """Return the provider's raw claims about the signed-in user."""
    if provider.oidc:
        id_token = token.get("id_token")
        if not id_token:
            raise HTTPException(status_code=502, detail="Provider did not return an ID token")
        # PyJWKClient fetches keys synchronously; keep it off the event loop.
        return await run_in_threadpool(verify_id_token, provider, id_token, nonce)

    headers = {"Accept": "application/vnd.github+json"} if provider.name == "github" else {}
    try:
        async with _oauth_client(provider, token=token) as client:
            resp = await client.get(provider.userinfo_url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Failed to fetch userinfo from {provider.name}")
            userinfo = resp.json()

            # GitHub: only a primary, verified address counts as the user's email.
            if provider.name == "github":
                userinfo["email_verified"] = False
                emails_resp = await client.get("https://api.github.com/user/emails", headers=headers)
                if emails_resp.status_code == 200:
                    primary = next((e for e in emails_resp.json() if e.get("primary") and e.get("verified")), None)
                    if primary:
                        userinfo["email"] = primary["email"]
                        userinfo["email_verified"] = True
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Userinfo request to %s failed: %s", provider.name, exc)
        raise HTTPException(status_code=502, detail=f"Failed to fetch userinfo from {provider.name}")
    return userinfo


def _extract_field(userinfo: dict, dotted_path: str):
    """Extract a nested field like 'picture.data.url' from a dict."""
    parts = dotted_path.split(".")
    val = userinfo
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def _normalize_userinfo(provider: OAuthProviderConfig, raw: dict) -> dict:
    """Normalize provider-specific userinfo to a standard format."""
    fm = provider.field_map
    result = {
        "provider_user_id": str(_extract_field(raw, fm.get("sub", "sub")) or ""),
        "email": _extract_field(raw, fm.get("email", "email")),
        "email_verified": raw.get("email_verified") is True,
        "name": _extract_field(raw, fm.get("name", "name")) or "",
        "given_name": raw.get("given_name", ""),
        "family_name": raw.get("family_name", ""),
        "picture": _extract_field(raw, fm.get("picture", "picture")),
        "username": _extract_field(raw, fm.get("username", "login")),
    }

    # Split name into given/family if provider doesn't provide them separately
    if not result["given_name"] and result["name"]:
        parts = result["name"].split(" ", 1)
        result["given_name"] = parts[0]
        result["family_name"] = parts[1] if len(parts) > 1 else ""

    return result


def _generate_unique_username(db: Session, base: str) -> str:
    """Generate a unique username from a base string."""
    # Clean the base
    clean = "".join(c for c in base if c.isalnum() or c in "-_")[:80]
    if not clean:
        clean = "user"

    candidate = clean
    counter = 1
    while get_user_by_username_db(db, candidate):
        suffix = secrets.token_hex(3)
        candidate = f"{clean}_{suffix}"
        counter += 1
        if counter > 10:
            candidate = f"user_{secrets.token_hex(6)}"
            break

    return candidate


async def handle_sso_callback(
    db: Session,
    provider_name: str,
    code: str,
    state: str,
    request: Request,
) -> dict:
    """Handle the SSO callback after user authorizes with provider.

    Returns a token dict (login) or {"message": ...} (link).
    """
    cookie_state = request.cookies.get("genesis_sso_state", "") if request else ""
    if not cookie_state or not secrets.compare_digest(cookie_state.encode("utf-8"), state.encode("utf-8")):
        raise HTTPException(status_code=400, detail="SSO state does not match this browser")
    state_data = validate_state(state)
    provider = get_provider(provider_name)

    if state_data["provider"] != provider_name:
        raise HTTPException(status_code=400, detail="State/provider mismatch")

    token = await exchange_code_for_tokens(provider, code, state_data.get("code_verifier"))
    raw_userinfo = await fetch_identity(provider, token, state_data.get("nonce"))
    userinfo = _normalize_userinfo(provider, raw_userinfo)

    if not userinfo["provider_user_id"]:
        raise HTTPException(status_code=502, detail="Provider did not return a user ID")

    # Database work is synchronous; run it in the threadpool.
    if state_data.get("action") == "link":
        return await run_in_threadpool(_handle_link, db, state_data, provider, userinfo)
    return await run_in_threadpool(_handle_login_or_register, db, provider, userinfo, request)


def _handle_login_or_register(
    db: Session,
    provider: OAuthProviderConfig,
    userinfo: dict,
    request: Request,
) -> dict:
    """Handle SSO login: returning user, auto-link, or new account."""

    # Case A: Returning SSO user (matched on provider + provider's user id)
    oauth_account = get_oauth_account_by_provider_db(db, provider.name, userinfo["provider_user_id"])
    if oauth_account:
        user = oauth_account.user
        if user.disabled or not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")
        return _issue_tokens(db, user, provider.name, request)

    # Case B: Email matches an existing account. Link automatically only when
    # BOTH sides have proven the address. Otherwise someone could pre-register
    # the victim's email with their own password and inherit the victim's later
    # SSO sign-in.
    if userinfo.get("email"):
        existing_user = get_user_by_email_db(db, userinfo["email"])
        if existing_user:
            if existing_user.disabled or not existing_user.is_active:
                raise HTTPException(status_code=403, detail="User account is deactivated")
            if existing_user.email_verified and userinfo.get("email_verified") is True:
                _create_oauth_account(db, str(existing_user.id), provider, userinfo)
                security_event("sso_auto_linked", user_id=str(existing_user.id), provider=provider.name)
                return _issue_tokens(db, existing_user, provider.name, request)
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. "
                f"Sign in with your existing credentials, then link {provider.name} from your profile.",
            )

    # Case C: Entirely new user
    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="SSO provider did not return an email address")

    username_base = userinfo.get("username") or email.split("@")[0]
    username = _generate_unique_username(db, username_base)

    from app.models.user_db_model import User as UserModel
    new_user = UserModel(
        username=username,
        email=email,
        password=None,
        is_active=True,
        email_verified=userinfo.get("email_verified", False),
        email_verified_at=datetime.utcnow() if userinfo.get("email_verified") else None,
        auth_provider=provider.name,
        auth_provider_id=userinfo["provider_user_id"],
        is_native=False,
    )
    db.add(new_user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account already exists; please retry sign-in")

    # Create profile from provider data
    from app.models.profile_db_model import Profile as ProfileModel
    profile = ProfileModel(
        user_id=str(new_user.id),
        given_name=userinfo.get("given_name", ""),
        family_name=userinfo.get("family_name", ""),
        nick_name=userinfo.get("username"),
        picture=userinfo.get("picture"),
        email=email,
        sub=str(new_user.id),
    )
    db.add(profile)
    db.flush()

    _create_oauth_account(db, str(new_user.id), provider, userinfo)
    security_event("sso_registered", user_id=str(new_user.id), provider=provider.name)

    return _issue_tokens(db, new_user, provider.name, request)


def _handle_link(
    db: Session,
    state_data: dict,
    provider: OAuthProviderConfig,
    userinfo: dict,
) -> dict:
    """Link an SSO provider to an existing authenticated user."""
    user_id = state_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="No user context for link action")

    # Check if this provider account is already linked to someone else
    existing = get_oauth_account_by_provider_db(db, provider.name, userinfo["provider_user_id"])
    if existing:
        if existing.user_id == user_id:
            return {"message": f"{provider.name} is already linked to your account", "user_id": user_id}
        raise HTTPException(
            status_code=409,
            detail=f"This {provider.name} account is already linked to a different user",
        )

    # Check user doesn't already have this provider linked
    existing_for_user = get_oauth_account_by_user_and_provider_db(db, user_id, provider.name)
    if existing_for_user:
        return {"message": f"{provider.name} is already linked to your account", "user_id": user_id}

    _create_oauth_account(db, user_id, provider, userinfo)
    security_event("sso_linked", user_id=user_id, provider=provider.name)

    return {"message": f"{provider.name} account linked successfully", "user_id": user_id}


def issue_tokens_for_user(db: Session, user_id: str, provider_name: str, request: Request) -> dict:
    """New session after a completed link, so the web app (whose in-memory
    tokens were lost on the round trip to the provider) can continue."""
    from app.database.user_db_interface import get_user_by_id_db
    user = get_user_by_id_db(db, user_id)
    if not user or user.disabled or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")
    return _issue_tokens(db, user, provider_name, request)


def unlink_provider(db: Session, user_id: str, provider_name: str) -> dict:
    """Unlink an SSO provider from a user's account."""
    # Keep concurrent unlink requests from removing the last two login methods.
    from app.models.user_db_model import User
    from app.models.oauth_account_db_model import OAuthAccount
    user = db.query(User).filter(User.id == user_id).with_for_update().populate_existing().first()
    if not user or user.disabled or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")
    all_accounts = db.query(OAuthAccount).filter(OAuthAccount.user_id == user_id).with_for_update().populate_existing().all()
    oauth_account = next((account for account in all_accounts if account.provider == provider_name), None)
    if not oauth_account:
        raise HTTPException(status_code=404, detail=f"{provider_name} is not linked to your account")

    # Prevent unlinking if user has no password (would lock them out)
    if not user.password and len(all_accounts) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot unlink the only authentication method. Set a password first.",
        )

    db.delete(oauth_account)
    db.commit()
    security_event("sso_unlinked", user_id=user_id, provider=provider_name)
    return {"message": f"{provider_name} account unlinked successfully"}


def get_linked_providers(db: Session, user_id: str) -> list[dict]:
    """List all linked SSO providers for a user."""
    from app.database.oauth_account_db_interface import get_oauth_accounts_by_user_db
    accounts = get_oauth_accounts_by_user_db(db, user_id)
    return [
        {
            "provider": a.provider,
            "provider_email": a.provider_email,
            "provider_username": a.provider_username,
            "linked_at": a.created_at,
        }
        for a in accounts
    ]


# ---- Hand-off to the web app ----
# The provider redirects the browser to the API. The API then redirects to the
# web app with a one-time code in the URL fragment (never sent to servers or
# logged), and binds that code to this browser with an HttpOnly cookie, so a
# code planted in someone else's browser cannot sign them in (login CSRF).

def _binding_hash(binding: str) -> str:
    return hashlib.sha256(binding.encode("utf-8")).hexdigest()


def create_login_handoff(tokens: dict) -> tuple[str, str]:
    """Returns (one-time code for the URL fragment, binding value for the cookie)."""
    code = secrets.token_urlsafe(32)
    binding = secrets.token_urlsafe(32)
    try:
        get_security_store().put_state(
            f"handoff:{code}", {"tokens": tokens, "binding": _binding_hash(binding)}, HANDOFF_TTL_SECONDS
        )
    except SecurityStoreUnavailable:
        raise _store_unavailable()
    return code, binding


def redeem_login_handoff(code: str, binding: str | None) -> dict:
    """Single use: a wrong or missing binding still consumes the code."""
    try:
        data = get_security_store().pop_state(f"handoff:{code}")
    except SecurityStoreUnavailable:
        raise _store_unavailable()
    if not data or not binding or not secrets.compare_digest(_binding_hash(binding), data["binding"]):
        raise HTTPException(status_code=400, detail="Invalid or expired sign-in code")
    return data["tokens"]


# ---- Internal helpers ----

def _issue_tokens(db: Session, user, provider_name: str, request: Request) -> dict:
    """Create session and issue JWT tokens for an SSO-authenticated user."""
    refresh_jti = str(uuid4())

    session_id = create_session(
        db=db,
        user_id=str(user.id),
        refresh_jti=refresh_jti,
        request=request,
        login_method=provider_name,
    )

    payload = build_user_claims(user, sid=session_id, auth_method=provider_name)

    access_token, _ = create_access_token(data=payload)
    refresh_token, _ = create_refresh_token(data={**payload, "jti_override": refresh_jti})

    # Update login tracking
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request and request.client else None
    user.last_login_method = provider_name
    db.commit()
    security_event("login_succeeded", user_id=str(user.id), method=provider_name)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def _create_oauth_account(db: Session, user_id: str, provider: OAuthProviderConfig, userinfo: dict):
    """Insert an oauth_accounts row linking a user to a provider (identity only)."""
    create_oauth_account_db(db, {
        "user_id": user_id,
        "provider": provider.name,
        "provider_user_id": userinfo["provider_user_id"],
        "provider_email": userinfo.get("email"),
        "provider_username": userinfo.get("username"),
    })
