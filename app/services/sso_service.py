"""SSO service: handles OAuth2 authorization code flow for Google, GitHub, Facebook."""

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from uuid import uuid4

import httpx
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.oauth_providers import get_provider, OAuthProviderConfig
from app.auth.auth import create_access_token, create_refresh_token
from app.database.oauth_account_db_interface import (
    create_oauth_account_db,
    get_oauth_account_by_provider_db,
    get_oauth_account_by_user_and_provider_db,
    delete_oauth_account_db,
    update_oauth_account_tokens_db,
)
from app.database.user_db_interface import get_user_by_email_db, create_user_db, get_user_by_username_db
from app.database.profile_db_interface import create_profile_db
from app.models.user_api_model import UserCreate
from app.models.profile_api_model import ProfileCreate
from app.services.session_service import create_session
from app.config import get_settings

settings = get_settings()

# In-memory state store for CSRF protection (use Redis/DB in production at scale)
_sso_states: dict[str, dict] = {}


def generate_authorize_url(provider_name: str, action: str = "login", user_id: str | None = None) -> tuple[str, str]:
    """Build the provider's authorization URL with state parameter.

    Returns (authorize_url, state).
    """
    provider = get_provider(provider_name)

    state = secrets.token_urlsafe(32)
    _sso_states[state] = {
        "provider": provider_name,
        "action": action,  # "login" or "link"
        "user_id": user_id,  # set when action=link
        "created_at": datetime.utcnow().isoformat(),
    }

    params = {
        "client_id": provider.client_id,
        "redirect_uri": provider.redirect_uri,
        "scope": " ".join(provider.scopes),
        "state": state,
        "response_type": "code",
    }

    # Google requires access_type for refresh tokens
    if provider_name == "google":
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{provider.authorize_url}?{query}", state


def validate_state(state: str) -> dict:
    """Validate and consume a state parameter. Returns state data or raises."""
    state_data = _sso_states.pop(state, None)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    # Check expiry (10 min)
    created = datetime.fromisoformat(state_data["created_at"])
    if datetime.utcnow() - created > timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="State parameter expired")

    return state_data


async def exchange_code_for_tokens(provider: OAuthProviderConfig, code: str) -> dict:
    """Exchange authorization code for provider access token."""
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "redirect_uri": provider.redirect_uri,
        }

        # GitHub needs grant_type differently
        if provider.name == "github":
            headers = {"Accept": "application/json"}
        else:
            data["grant_type"] = "authorization_code"
            headers = {}

        resp = await client.post(provider.token_url, data=data, headers=headers)

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Failed to exchange code with {provider.name}")

        token_data = resp.json()

        if "error" in token_data:
            raise HTTPException(
                status_code=502,
                detail=f"{provider.name} token error: {token_data.get('error_description', token_data['error'])}",
            )

        return token_data


async def fetch_userinfo(provider: OAuthProviderConfig, access_token: str) -> dict:
    """Fetch user profile from the provider."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}

        # GitHub needs a different Accept header
        if provider.name == "github":
            headers["Accept"] = "application/vnd.github+json"

        resp = await client.get(provider.userinfo_url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Failed to fetch userinfo from {provider.name}")

        userinfo = resp.json()

        # GitHub: email may not be in the user response, fetch from /user/emails
        if provider.name == "github" and not userinfo.get("email"):
            emails_resp = await client.get("https://api.github.com/user/emails", headers=headers)
            if emails_resp.status_code == 200:
                emails = emails_resp.json()
                primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                if primary:
                    userinfo["email"] = primary["email"]
                    userinfo["email_verified"] = True

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
        "email_verified": raw.get("email_verified", False),
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

    # GitHub treats verified emails from the emails endpoint
    if provider.name == "github":
        result["email_verified"] = True  # We only use verified emails from GitHub

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

    Returns token dict (access_token, refresh_token, token_type).
    """
    state_data = validate_state(state)
    provider = get_provider(provider_name)

    if state_data["provider"] != provider_name:
        raise HTTPException(status_code=400, detail="State/provider mismatch")

    # Exchange code for provider tokens
    token_data = await exchange_code_for_tokens(provider, code)
    provider_access_token = token_data.get("access_token")
    provider_refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")

    if not provider_access_token:
        raise HTTPException(status_code=502, detail="No access token from provider")

    # Fetch user profile from provider
    raw_userinfo = await fetch_userinfo(provider, provider_access_token)
    userinfo = _normalize_userinfo(provider, raw_userinfo)

    if not userinfo["provider_user_id"]:
        raise HTTPException(status_code=502, detail="Provider did not return a user ID")

    action = state_data.get("action", "login")

    if action == "link":
        return _handle_link(db, state_data, provider, userinfo, provider_access_token, provider_refresh_token, expires_in, raw_userinfo)

    # --- LOGIN / REGISTER flow ---
    return _handle_login_or_register(
        db, provider, userinfo, provider_access_token, provider_refresh_token, expires_in, raw_userinfo, request,
    )


def _handle_login_or_register(
    db: Session,
    provider: OAuthProviderConfig,
    userinfo: dict,
    provider_access_token: str,
    provider_refresh_token: str | None,
    expires_in: int | None,
    raw_userinfo: dict,
    request: Request,
) -> dict:
    """Handle SSO login: returning user, auto-link, or new account."""

    # Case A: Returning SSO user
    oauth_account = get_oauth_account_by_provider_db(db, provider.name, userinfo["provider_user_id"])
    if oauth_account:
        user = oauth_account.user
        if user.disabled or not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")

        # Update provider tokens
        _update_provider_tokens(db, oauth_account.id, provider_access_token, provider_refresh_token, expires_in)

        return _issue_tokens(db, user, provider.name, request)

    # Case B: Email matches existing native account
    if userinfo.get("email"):
        existing_user = get_user_by_email_db(db, userinfo["email"])
        if existing_user:
            if not existing_user.email_verified and userinfo.get("email_verified"):
                # Auto-verify since provider verified the email
                existing_user.email_verified = True
                existing_user.email_verified_at = datetime.utcnow()
                db.commit()

            if existing_user.email_verified or userinfo.get("email_verified"):
                # Auto-link
                _create_oauth_account(
                    db, str(existing_user.id), provider, userinfo,
                    provider_access_token, provider_refresh_token, expires_in, raw_userinfo,
                )
                return _issue_tokens(db, existing_user, provider.name, request)
            else:
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email exists but is not verified. "
                    "Log in with your password and verify your email, then link this SSO provider.",
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
    db.commit()
    db.refresh(new_user)

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
    db.commit()

    # Create oauth_account link
    _create_oauth_account(
        db, str(new_user.id), provider, userinfo,
        provider_access_token, provider_refresh_token, expires_in, raw_userinfo,
    )

    return _issue_tokens(db, new_user, provider.name, request)


def _handle_link(
    db: Session,
    state_data: dict,
    provider: OAuthProviderConfig,
    userinfo: dict,
    provider_access_token: str,
    provider_refresh_token: str | None,
    expires_in: int | None,
    raw_userinfo: dict,
) -> dict:
    """Link an SSO provider to an existing authenticated user."""
    user_id = state_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="No user context for link action")

    # Check if this provider account is already linked to someone else
    existing = get_oauth_account_by_provider_db(db, provider.name, userinfo["provider_user_id"])
    if existing:
        if existing.user_id == user_id:
            return {"message": f"{provider.name} is already linked to your account"}
        raise HTTPException(
            status_code=409,
            detail=f"This {provider.name} account is already linked to a different user",
        )

    # Check user doesn't already have this provider linked
    existing_for_user = get_oauth_account_by_user_and_provider_db(db, user_id, provider.name)
    if existing_for_user:
        return {"message": f"{provider.name} is already linked to your account"}

    _create_oauth_account(
        db, user_id, provider, userinfo,
        provider_access_token, provider_refresh_token, expires_in, raw_userinfo,
    )

    return {"message": f"{provider.name} account linked successfully"}


def unlink_provider(db: Session, user_id: str, provider_name: str) -> dict:
    """Unlink an SSO provider from a user's account."""
    oauth_account = get_oauth_account_by_user_and_provider_db(db, user_id, provider_name)
    if not oauth_account:
        raise HTTPException(status_code=404, detail=f"{provider_name} is not linked to your account")

    # Prevent unlinking if user has no password (would lock them out)
    from app.database.user_db_interface import get_user_by_id_db
    user = get_user_by_id_db(db, user_id)
    from app.database.oauth_account_db_interface import get_oauth_accounts_by_user_db
    all_accounts = get_oauth_accounts_by_user_db(db, user_id)

    if not user.password and len(all_accounts) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot unlink the only authentication method. Set a password first.",
        )

    delete_oauth_account_db(db, oauth_account.id)
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

    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "auth_method": provider_name,
        "scope": "openid profile email",
        "sid": session_id,
    }

    access_token, _ = create_access_token(data=payload)
    refresh_token, _ = create_refresh_token(data={**payload, "jti_override": refresh_jti})

    # Update login tracking
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    user.last_login_method = provider_name
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def _create_oauth_account(
    db: Session,
    user_id: str,
    provider: OAuthProviderConfig,
    userinfo: dict,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    raw_userinfo: dict,
):
    """Insert an oauth_accounts row linking a user to a provider."""
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    create_oauth_account_db(db, {
        "user_id": user_id,
        "provider": provider.name,
        "provider_user_id": userinfo["provider_user_id"],
        "provider_email": userinfo.get("email"),
        "provider_username": userinfo.get("username"),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": token_expires_at,
        "raw_userinfo": raw_userinfo,
    })


def _update_provider_tokens(db: Session, account_id: str, access_token: str, refresh_token: str | None, expires_in: int | None):
    """Update cached provider tokens on an oauth_account."""
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    update_oauth_account_tokens_db(db, account_id, access_token, refresh_token, token_expires_at)
