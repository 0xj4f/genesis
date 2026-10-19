"""OIDC Provider service: authorization code flow, token exchange, userinfo, ID tokens."""

import secrets
import hashlib
import base64
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.auth import build_user_claims, create_access_token, create_refresh_token
from app.auth.keys import get_signing_key
from app.auth.throttle import client_key, ensure_attempt_allowed, record_failure, record_success
from app.config import get_settings
from app.database.oauth_client_db_interface import get_oauth_client_by_id_db
from app.database.authz_code_db_interface import create_authz_code_db, get_authz_code_db, mark_authz_code_used_db
from app.database.user_db_interface import get_user_by_id_db
from app.database.profile_db_interface import get_profile_by_user_db
from app.services.session_service import create_session
from app.utils.audit import security_event
from app.utils.security import verify_client_secret

settings = get_settings()


def get_openid_configuration() -> dict:
    """Return the OpenID Connect discovery document."""
    issuer = settings.OAUTH_ISSUER
    # The browser-facing authorize step (sign-in + consent) lives in the web app
    # when it is configured; the API endpoint itself requires a bearer token.
    authorization_endpoint = (
        f"{settings.frontend_url}/oauth/authorize" if settings.frontend_url else f"{issuer}/oauth/authorize"
    )
    return {
        "issuer": issuer,
        "authorization_endpoint": authorization_endpoint,
        "token_endpoint": f"{issuer}/oauth/token",
        "userinfo_endpoint": f"{issuer}/oauth/userinfo",
        "jwks_uri": f"{issuer}/.well-known/jwks.json",
        "registration_endpoint": None,
        "scopes_supported": ["openid", "profile", "email", "offline_access"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "claims_supported": [
            "sub", "iss", "aud", "exp", "iat", "auth_time",
            "name", "given_name", "family_name", "nickname",
            "email", "email_verified", "picture", "locale",
        ],
        "code_challenge_methods_supported": ["S256"],
    }


def authenticate_client(db: Session, client, client_secret: str | None) -> None:
    """Verify a confidential client's secret (throttled per client).
    Legacy bcrypt secret hashes are upgraded to SHA-256 on first success."""
    key = client_key(str(client.id))
    ensure_attempt_allowed(key)
    if not client_secret:
        raise HTTPException(status_code=401, detail="Client authentication required")
    valid, upgraded_hash = verify_client_secret(client_secret, client.client_secret_hash)
    if not valid:
        record_failure(key)
        security_event("client_auth_failed", client_id=str(client.id))
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    record_success(key)
    if upgraded_hash:
        client.client_secret_hash = upgraded_hash
        db.commit()


def load_client_for_grant(db: Session, client_id: str, client_secret: str | None, grant_type: str):
    """Load an active client allowed to use grant_type, authenticating it when confidential."""
    client = get_oauth_client_by_id_db(db, client_id) if client_id else None
    if not client:
        raise HTTPException(status_code=401, detail="Unknown client")
    if grant_type not in (client.grant_types or []):
        raise HTTPException(status_code=400, detail=f"{grant_type} grant not allowed for this client")
    if client.is_confidential:
        authenticate_client(db, client, client_secret)
    return client


def get_public_client_info(db: Session, client_id: str) -> dict:
    """What the consent screen shows about a client. No secrets."""
    client = get_oauth_client_by_id_db(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Unknown client_id")
    return {
        "client_id": str(client.id),
        "client_name": client.client_name,
        "is_first_party": bool(client.is_first_party),
        "allowed_scopes": client.allowed_scopes or [],
    }


def authorization_redirect(redirect_uri: str, params: dict) -> str:
    separator = "&" if "?" in redirect_uri else "?"
    return f"{redirect_uri}{separator}{urlencode(params)}"


def validate_authorize_request(
    db: Session,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    scope: str,
    code_challenge: str | None,
    code_challenge_method: str | None,
) -> dict:
    """Validate an authorization request and return the client."""
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only response_type=code is supported")

    client = get_oauth_client_by_id_db(db, client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Unknown client_id")
    if "authorization_code" not in (client.grant_types or []):
        raise HTTPException(status_code=400, detail="authorization_code grant not allowed for this client")

    # Validate redirect_uri
    if redirect_uri not in (client.redirect_uris or []):
        raise HTTPException(status_code=400, detail="Invalid redirect_uri for this client")

    # Validate scopes
    requested_scopes = scope.split()
    for s in requested_scopes:
        if s not in (client.allowed_scopes or []):
            raise HTTPException(status_code=400, detail=f"Scope '{s}' not allowed for this client")

    # PKCE validation
    if code_challenge and code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Only code_challenge_method=S256 is supported")
    if code_challenge_method and not code_challenge:
        raise HTTPException(status_code=400, detail="code_challenge is required")
    if code_challenge and not re.fullmatch(r"[A-Za-z0-9_-]{43}", code_challenge):
        raise HTTPException(status_code=400, detail="Invalid S256 code_challenge")

    # Public clients must use PKCE
    if not client.is_confidential and not code_challenge:
        raise HTTPException(status_code=400, detail="Public clients must use PKCE (code_challenge required)")

    return {
        "client": client,
        "scopes": requested_scopes,
    }


def create_authorization_code(
    db: Session,
    client_id: str,
    user_id: str,
    redirect_uri: str,
    scope: str,
    nonce: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
) -> str:
    """Generate and store an authorization code. Returns the code."""
    code = secrets.token_urlsafe(48)  # 64 chars base64url

    create_authz_code_db(db, {
        "code": code,
        "client_id": client_id,
        "user_id": user_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
        "used": False,
    })

    return code


def exchange_authorization_code(
    db: Session,
    code: str,
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
    code_verifier: str | None,
    request=None,
) -> dict:
    """Exchange authorization code for tokens."""
    authz_code = get_authz_code_db(db, code)
    if not authz_code:
        raise HTTPException(status_code=400, detail="Invalid or expired authorization code")

    # Validate client
    if authz_code.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")

    client = get_oauth_client_by_id_db(db, client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Unknown client")
    if "authorization_code" not in (client.grant_types or []):
        raise HTTPException(status_code=400, detail="authorization_code grant not allowed for this client")

    # Authenticate confidential clients
    if client.is_confidential:
        authenticate_client(db, client, client_secret)

    # Validate redirect_uri
    if authz_code.redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")

    # PKCE verification
    if authz_code.code_challenge:
        if not code_verifier:
            raise HTTPException(status_code=400, detail="code_verifier required for PKCE")
        if not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", code_verifier):
            raise HTTPException(status_code=400, detail="Invalid code_verifier")
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        if not secrets.compare_digest(expected, authz_code.code_challenge):
            raise HTTPException(status_code=400, detail="Invalid code_verifier")

    # Load user
    user = get_user_by_id_db(db, authz_code.user_id)
    if not user or user.disabled or not user.is_active:
        raise HTTPException(status_code=400, detail="User account unavailable")

    # Atomic single-use claim, after validating the caller and before minting.
    if not mark_authz_code_used_db(db, code):
        raise HTTPException(status_code=400, detail="Invalid or expired authorization code")

    scopes = authz_code.scope.split()

    # Create session + tokens
    refresh_jti = str(uuid4())
    session_id = create_session(
        db=db,
        user_id=str(user.id),
        refresh_jti=refresh_jti,
        request=request,
        login_method="oidc",
    )

    # Include both the client_id and default audience so genesis can validate its own tokens
    audiences = sorted({client_id, settings.OAUTH_DEFAULT_AUDIENCE})
    payload = build_user_claims(user, sid=session_id, auth_method="oidc", scope=authz_code.scope)
    # client_id binds the refresh token to this client (checked at refresh time).
    payload.update({"aud": audiences, "client_id": client_id})

    access_token, _ = create_access_token(data=payload)

    result = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "scope": authz_code.scope,
    }

    # Issue a refresh token only when requested and allowed for this client
    if "offline_access" in scopes and "refresh_token" in (client.grant_types or []):
        refresh_token, _ = create_refresh_token(data={**payload, "jti_override": refresh_jti})
        result["refresh_token"] = refresh_token

    # Issue ID token if openid scope
    if "openid" in scopes:
        id_token = _create_id_token(user, client_id, authz_code.nonce, access_token, db)
        result["id_token"] = id_token

    # Update login tracking
    user.last_login_at = datetime.utcnow()
    user.last_login_method = "oidc"
    if request and request.client:
        user.last_login_ip = request.client.host
    db.commit()

    return result


def handle_client_credentials(db: Session, client_id: str, client_secret: str, scope: str | None) -> dict:
    """Issue tokens for machine-to-machine client_credentials grant."""
    client = get_oauth_client_by_id_db(db, client_id)
    if not client:
        raise HTTPException(status_code=401, detail="Unknown client")

    if "client_credentials" not in (client.grant_types or []):
        raise HTTPException(status_code=400, detail="client_credentials grant not allowed for this client")

    if not client.is_confidential:
        raise HTTPException(status_code=400, detail="client_credentials requires a confidential client")

    authenticate_client(db, client, client_secret)

    # Validate requested scopes
    requested_scopes = (scope or "").split()
    for s in requested_scopes:
        if s not in (client.allowed_scopes or []):
            raise HTTPException(status_code=400, detail=f"Scope '{s}' not allowed")

    audiences = list(set((client.allowed_audiences or []) + [settings.OAUTH_DEFAULT_AUDIENCE]))
    payload = {
        "sub": client_id,
        "scope": scope or "",
        "aud": audiences,
        "auth_method": "client_credentials",
        "client_id": client_id,
    }

    access_token, _ = create_access_token(data=payload)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "scope": scope or "",
    }


def get_userinfo(db: Session, user_id: str, scopes: list[str]) -> dict:
    """Build userinfo response based on granted scopes."""
    user = get_user_by_id_db(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = {"sub": str(user.id)}

    if "email" in scopes:
        result["email"] = user.email
        result["email_verified"] = user.email_verified

    if "profile" in scopes:
        profile = get_profile_by_user_db(db, str(user.id))
        if profile:
            result["name"] = f"{profile.given_name} {profile.family_name}".strip()
            result["given_name"] = profile.given_name
            result["family_name"] = profile.family_name
            if profile.nick_name:
                result["nickname"] = profile.nick_name
            if profile.picture:
                result["picture"] = profile.picture
            if profile.phone_verified is not None:
                result["phone_number_verified"] = profile.phone_verified
            result["updated_at"] = int(profile.updated_at.timestamp()) if profile.updated_at else None
        else:
            result["name"] = user.username

    return result


def _create_id_token(user, client_id: str, nonce: str | None, access_token: str, db: Session) -> str:
    """Create an OIDC ID Token (JWT)."""
    import jwt

    kid, key, algorithm = get_signing_key()
    now = datetime.now(timezone.utc)

    # at_hash: left half of SHA-256 of access_token
    at_hash_digest = hashlib.sha256(access_token.encode("ascii")).digest()
    at_hash = base64.urlsafe_b64encode(at_hash_digest[:16]).rstrip(b"=").decode("ascii")

    claims = {
        "iss": settings.OAUTH_ISSUER,
        "sub": str(user.id),
        "aud": client_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "auth_time": int(now.timestamp()),
        "at_hash": at_hash,
        "email": user.email,
        "email_verified": user.email_verified,
    }

    if nonce:
        claims["nonce"] = nonce

    # Add profile claims
    profile = get_profile_by_user_db(db, str(user.id))
    if profile:
        claims["name"] = f"{profile.given_name} {profile.family_name}".strip()
        claims["given_name"] = profile.given_name
        claims["family_name"] = profile.family_name
        if profile.picture:
            claims["picture"] = profile.picture

    headers = {"kid": kid} if kid else {}
    return jwt.encode(claims, key, algorithm=algorithm, headers=headers)
