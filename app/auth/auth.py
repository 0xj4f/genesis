from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import InvalidTokenError
from app.database.user_db_interface import get_user_by_username_db, get_user_by_id_db
from app.models.user_api_model import User, TokenData, UserMinimal
from app.utils.security import verify_and_update_password, verify_dummy_password
from app.utils.audit import security_event, subject_hash
from app.auth.throttle import login_key, ensure_attempt_allowed, record_failure, record_success
from app.database.session import get_db
from app.config import get_settings
from app.auth.keys import get_signing_key, get_verification_key_by_kid
from app.models.session_db_model import Session as LoginSession
import uuid

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def authenticate_user(db: Session, username: str, password: str):
    """Verify a username/password pair. Throttled per account; returns the user or False."""
    key = login_key(username)
    ensure_attempt_allowed(key)
    user = get_user_by_username_db(db, username)
    if not user or not user.password:
        # Same work as a real check so timing does not reveal unknown accounts.
        verify_dummy_password(password)
        valid = False
    else:
        valid, upgraded_hash = verify_and_update_password(password, user.password)
        if valid and upgraded_hash:
            # Outdated algorithm or parameters (e.g. bcrypt): store the new hash.
            user.password = upgraded_hash
            db.commit()
            security_event("password_rehashed", user_id=str(user.id))
    if not valid:
        record_failure(key)
        security_event("login_failed", subject=subject_hash(username))
        return False
    record_success(key)
    return user


def enforce_email_verified(user) -> None:
    """With EMAIL_VERIFY enabled, password sign-in requires a verified email."""
    if settings.EMAIL_VERIFY and not user.email_verified:
        raise HTTPException(status_code=403, detail="Email address not verified")


def build_user_claims(user, *, sid: str, auth_method: str, scope: str = "openid profile email") -> dict:
    """Claims shared by every user token, whichever way the user signed in.

    `role` is read by relying parties (gen-commerce) that validate tokens offline;
    it can be stale for up to the access-token lifetime after a role change.
    """
    return {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "auth_method": auth_method,
        "scope": scope,
        "sid": sid,
        "role": user.role,
    }


def create_token(data: dict, expires_delta: timedelta, token_type: str = "access") -> tuple[str, str]:
    kid, key, algorithm = get_signing_key()
    now = datetime.now(timezone.utc)

    # Allow caller to pre-assign a JTI (for session binding)
    jti = data.pop("jti_override", None) or str(uuid.uuid4())

    to_encode = {
        "iss": settings.OAUTH_ISSUER,
        "aud": data.get("aud", [settings.OAUTH_DEFAULT_AUDIENCE]),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": jti,
        **{k: v for k, v in data.items() if k != "aud"},
    }

    if token_type == "refresh":
        to_encode["token_type"] = "refresh"

    headers = {"kid": kid} if kid else {}

    encoded = jwt.encode(to_encode, key, algorithm=algorithm, headers=headers)
    return encoded, jti


def create_access_token(data: dict) -> tuple[str, str]:
    """Returns (token, jti)."""
    return create_token(data, timedelta(minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES), token_type="access")


def create_refresh_token(data: dict) -> tuple[str, str]:
    """Returns (token, jti)."""
    return create_token(data, timedelta(days=settings.OAUTH_REFRESH_TOKEN_TTL_DAYS), token_type="refresh")


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The JWT string
        expected_type: "access" or "refresh" - validates token_type claim
    """
    try:
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid", "")

        # Resolve verification key
        key_result = get_verification_key_by_kid(kid)
        if key_result is None:
            raise HTTPException(status_code=401, detail="Unknown signing key")

        key, algorithm = key_result

        # Decode with full validation
        decoded = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=settings.OAUTH_DEFAULT_AUDIENCE,
            issuer=settings.OAUTH_ISSUER,
            options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub", "jti"]},
        )

        # Validate token type
        token_type = decoded.get("token_type", "access")
        if expected_type == "refresh" and token_type != "refresh":
            raise HTTPException(status_code=401, detail="Expected refresh token")
        if expected_type == "access" and token_type == "refresh":
            raise HTTPException(status_code=401, detail="Refresh token cannot be used as access token")

        return decoded
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _authenticate_access_token(token: str, db: Session):
    """Validate an access token and its session. Returns (user, claims, session)."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token=token, expected_type="access")
    user_id: str = payload.get("sub")

    if user_id is None:
        raise credentials_exception

    user = get_user_by_id_db(db=db, user_id=user_id)

    if user is None:
        raise credentials_exception
    if user.disabled or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")
    session = validate_access_session(db, payload)
    return user, payload, session


def oauth_authenticate_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Validate access token and return the authenticated user."""
    return _authenticate_access_token(token, db)[0]


def current_user_with_claims(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Like oauth_authenticate_current_user, but also returns (claims, session)
    for endpoints that need the session id or sign-in time."""
    return _authenticate_access_token(token, db)


def validate_access_session(db: Session, payload: dict):
    sid = payload.get("sid")
    if not sid:
        raise HTTPException(status_code=401, detail="Token is not bound to a session")
    session = db.query(LoginSession).filter(
        LoginSession.id == sid,
        LoginSession.user_id == payload.get("sub"),
        LoginSession.is_active == True,  # noqa: E712
        LoginSession.expires_at > datetime.utcnow(),
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    return session


def require_reauth(db: Session, user, session, current_password) -> None:
    """Confirm the caller still controls the account before a sensitive change.

    Accounts with a password must supply it (throttled like a login). SSO-only
    accounts must have signed in within REAUTH_MAX_AGE_SECONDS instead.
    """
    if user.password:
        if not current_password:
            raise HTTPException(status_code=400, detail="current_password is required")
        key = login_key(user.username)
        ensure_attempt_allowed(key)
        valid, upgraded_hash = verify_and_update_password(current_password.get_secret_value(), user.password)
        if not valid:
            record_failure(key)
            security_event("reauth_failed", user_id=str(user.id))
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        record_success(key)
        if upgraded_hash:
            user.password = upgraded_hash
        return
    signed_in_at = session.created_at
    if signed_in_at is None or datetime.utcnow() - signed_in_at > timedelta(seconds=settings.REAUTH_MAX_AGE_SECONDS):
        raise HTTPException(status_code=403, detail="Please sign in again to make this change")


def require_role(*allowed_roles):
    """Factory that returns a FastAPI dependency enforcing role-based access.

    Usage: current_user=Depends(require_role("admin", "root"))
    """
    # A plain def: FastAPI runs it in the threadpool, so the blocking database
    # lookups do not stall the event loop.
    def _check(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
    ):
        user = oauth_authenticate_current_user(token, db)
        if user.role not in allowed_roles:
            security_event("authz_denied", actor=str(user.id), role=user.role, action="role_required")
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


require_admin = require_role("admin", "root")
require_root = require_role("root")


def oauth_authenticate_internal_service(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserMinimal:
    """Validate token for internal service-to-service calls."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token=token, expected_type="access")
    user_id = payload.get("sub")
    # For backwards compat, also check user_id claim
    if not user_id:
        user_id = payload.get("user_id")
    username = payload.get("username", "")

    if not user_id:
        raise credentials_exception

    if payload.get("auth_method") != "client_credentials":
        oauth_authenticate_current_user(token, db)

    return UserMinimal(user_id=user_id, username=username)
