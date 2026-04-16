"""OIDC Provider service: authorization code flow, token exchange, userinfo, ID tokens."""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.auth import create_access_token, create_refresh_token
from app.auth.keys import get_signing_key
from app.config import get_settings
from app.database.oauth_client_db_interface import get_oauth_client_by_id_db
from app.database.authz_code_db_interface import create_authz_code_db, get_authz_code_db, mark_authz_code_used_db
from app.database.user_db_interface import get_user_by_id_db
from app.database.profile_db_interface import get_profile_by_user_db
from app.services.session_service import create_session
from app.utils.security import verify_password

settings = get_settings()


def get_openid_configuration() -> dict:
    """Return the OpenID Connect discovery document."""
    issuer = settings.OAUTH_ISSUER
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
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

    # Authenticate confidential clients
    if client.is_confidential:
        if not client_secret:
            raise HTTPException(status_code=401, detail="Client authentication required")
        if not verify_password(client_secret, client.client_secret_hash):
            raise HTTPException(status_code=401, detail="Invalid client credentials")

    # Validate redirect_uri
    if authz_code.redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")

    # PKCE verification
    if authz_code.code_challenge:
        if not code_verifier:
            raise HTTPException(status_code=400, detail="code_verifier required for PKCE")
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        if expected != authz_code.code_challenge:
            raise HTTPException(status_code=400, detail="Invalid code_verifier")

    # Mark code as used
    mark_authz_code_used_db(db, code)

    # Load user
    user = get_user_by_id_db(db, authz_code.user_id)
    if not user or user.disabled or not user.is_active:
        raise HTTPException(status_code=400, detail="User account unavailable")

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
    audiences = list({client_id, settings.OAUTH_DEFAULT_AUDIENCE})
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "auth_method": "oidc",
        "scope": authz_code.scope,
        "sid": session_id,
        "aud": audiences,
    }

    access_token, _ = create_access_token(data=payload)

    result = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "scope": authz_code.scope,
    }

    # Issue refresh token if offline_access scope
    if "offline_access" in scopes:
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

    if not verify_password(client_secret, client.client_secret_hash):
        raise HTTPException(status_code=401, detail="Invalid client credentials")

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
            if profile.locale:
                result["locale"] = profile.locale
            result["updated_at"] = int(profile.updated_at.timestamp()) if profile.updated_at else None
        else:
            result["name"] = user.username

    return result


def _create_id_token(user, client_id: str, nonce: str | None, access_token: str, db: Session) -> str:
    """Create an OIDC ID Token (JWT)."""
    from jose import jwt as jose_jwt

    kid, key, algorithm = get_signing_key()
    now = datetime.utcnow()

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
    return jose_jwt.encode(claims, key, algorithm=algorithm, headers=headers)
