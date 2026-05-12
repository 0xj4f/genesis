from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.database.user_db_interface import get_user_by_username_db, get_user_by_id_db
from app.models.user_api_model import User, TokenData, UserMinimal
from app.utils.security import verify_password
from app.database.session import get_db
from app.config import get_settings
from app.auth.keys import get_signing_key, get_verification_key_by_kid
import uuid

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username_db(db, username)
    if not user or not user.password or not verify_password(password, user.password):
        return False
    return user


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
            options={"require_exp": True, "require_iat": True, "require_nbf": True},
        )

        # Validate token type
        token_type = decoded.get("token_type", "access")
        if expected_type == "refresh" and token_type != "refresh":
            raise HTTPException(status_code=401, detail="Expected refresh token")
        if expected_type == "access" and token_type == "refresh":
            raise HTTPException(status_code=401, detail="Refresh token cannot be used as access token")

        return decoded
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def oauth_authenticate_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Validate access token and return the authenticated user."""
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
    return user


def require_role(*allowed_roles):
    """Factory that returns a FastAPI dependency enforcing role-based access.

    Usage: current_user=Depends(require_role("admin", "root"))
    """
    async def _check(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
    ):
        user = oauth_authenticate_current_user(token, db)
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


require_admin = require_role("admin", "root")
require_root = require_role("root")


def oauth_authenticate_internal_service(token: str = Depends(oauth2_scheme)) -> UserMinimal:
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

    return UserMinimal(user_id=user_id, username=username)
