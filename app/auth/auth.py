import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.profile_db_model import Profile
from app.models.user_db_model import (
    AuditLog,
    AuthProvider,
    Session as UserSession,
    User,
    UserCredential,
    UserIdentity,
    UserRole,
    UserStatus,
)
from app.utils.security import hash_password, verify_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
ISSUER = os.getenv("OAUTH_ISSUER", "genesis")
AUDIENCE = os.getenv("OAUTH_AUDIENCE", "genesis-api")
SECRET_KEY = os.getenv("OAUTH_SECRET_KEY")
ALGORITHM = os.getenv("OAUTH_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("OAUTH_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


if not SECRET_KEY:
    raise RuntimeError("Missing OAUTH_SECRET_KEY. Refusing to start with insecure defaults.")


def _now() -> datetime:
    return datetime.utcnow()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_token(payload: dict, expires_delta: timedelta) -> str:
    now = _now()
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": str(uuid.uuid4()),
        **payload,
    }
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(*, user_id: str, role: UserRole, sid: str, amr: str) -> str:
    return _create_token(
        {
            "sub": user_id,
            "role": role.value,
            "sid": sid,
            "amr": amr,
            "token_type": "access",
        },
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(*, user_id: str, sid: str) -> str:
    return _create_token(
        {
            "sub": user_id,
            "sid": sid,
            "token_type": "refresh",
        },
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require_exp": True, "require_iat": True, "require_nbf": True},
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def write_audit_log(
    db: Session,
    *,
    actor_user_id: str,
    action: str,
    target_type: str,
    target_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata or {},
    )
    db.add(log)
    db.commit()


def create_session_tokens(
    db: Session,
    *,
    user: User,
    identity: UserIdentity,
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> dict:
    session = UserSession(
        user_id=user.id,
        identity_id=identity.id,
        jti=str(uuid.uuid4()),
        refresh_token_hash="pending",
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.flush()

    access_token = create_access_token(user_id=user.id, role=user.role, sid=session.id, amr=identity.provider.value)
    refresh_token = create_refresh_token(user_id=user.id, sid=session.id)
    session.refresh_token_hash = _hash_token(refresh_token)

    identity.last_login_at = _now()
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def authenticate_native_user(db: Session, username_or_email: str, password: str) -> tuple[User, UserIdentity]:
    identity = (
        db.query(UserIdentity)
        .filter(UserIdentity.provider == AuthProvider.native)
        .filter((UserIdentity.username == username_or_email) | (UserIdentity.email == username_or_email))
        .first()
    )
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = db.query(User).filter(User.id == identity.user_id).first()
    creds = db.query(UserCredential).filter(UserCredential.user_id == identity.user_id).first()
    if not user or not creds or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, creds.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user, identity


def register_native_user(db: Session, *, username: str, email: str, password: str) -> User:
    existing = (
        db.query(UserIdentity)
        .filter(UserIdentity.provider == AuthProvider.native)
        .filter((UserIdentity.username == username) | (UserIdentity.email == email))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(role=UserRole.user, status=UserStatus.active)
    db.add(user)
    db.flush()

    identity = UserIdentity(
        user_id=user.id,
        provider=AuthProvider.native,
        provider_user_id=username,
        username=username,
        email=email,
        email_verified=False,
    )
    db.add(identity)

    creds = UserCredential(user_id=user.id, password_hash=hash_password(password))
    db.add(creds)

    profile = Profile(user_id=user.id, given_name=username, family_name="", nick_name=username)
    db.add(profile)
    db.commit()

    write_audit_log(db, actor_user_id=user.id, action="register_native", target_type="user", target_id=user.id)
    return user


def find_or_create_oauth_user(
    db: Session,
    *,
    provider: AuthProvider,
    provider_user_id: str,
    email: Optional[str],
    email_verified: bool,
    given_name: Optional[str],
    family_name: Optional[str],
    picture_url: Optional[str],
) -> tuple[User, UserIdentity]:
    identity = (
        db.query(UserIdentity)
        .filter(UserIdentity.provider == provider, UserIdentity.provider_user_id == provider_user_id)
        .first()
    )
    if identity:
        user = db.query(User).filter(User.id == identity.user_id).first()
        if not user or user.status != UserStatus.active:
            raise HTTPException(status_code=403, detail="User is disabled")
        return user, identity

    user = User(role=UserRole.user, status=UserStatus.active)
    db.add(user)
    db.flush()

    identity = UserIdentity(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        email_verified=email_verified,
    )
    db.add(identity)

    profile = Profile(
        user_id=user.id,
        given_name=given_name or provider.value,
        family_name=family_name or "user",
        picture_url=picture_url,
    )
    db.add(profile)
    db.commit()

    write_audit_log(
        db,
        actor_user_id=user.id,
        action=f"register_{provider.value}",
        target_type="user",
        target_id=user.id,
    )
    return user, identity


def rotate_refresh_token(
    db: Session,
    *,
    refresh_token: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> dict:
    payload = decode_token(refresh_token)
    if payload.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    sid = payload.get("sid")
    user_id = payload.get("sub")
    if not sid or not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    session = db.query(UserSession).filter(UserSession.id == sid, UserSession.user_id == user_id).first()
    if not session or session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Session revoked or missing")

    if session.expires_at < _now():
        raise HTTPException(status_code=401, detail="Session expired")

    if session.refresh_token_hash != _hash_token(refresh_token):
        raise HTTPException(status_code=401, detail="Refresh token replay detected")

    user = db.query(User).filter(User.id == session.user_id).first()
    identity = db.query(UserIdentity).filter(UserIdentity.id == session.identity_id).first()
    if not user or not identity or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="Invalid user session")

    session.ip_address = ip_address or session.ip_address
    session.user_agent = user_agent or session.user_agent

    access_token = create_access_token(user_id=user.id, role=user.role, sid=session.id, amr=identity.provider.value)
    new_refresh_token = create_refresh_token(user_id=user.id, sid=session.id)
    session.refresh_token_hash = _hash_token(new_refresh_token)
    db.commit()

    write_audit_log(db, actor_user_id=user.id, action="refresh", target_type="session", target_id=session.id)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def revoke_session_from_refresh_token(db: Session, *, refresh_token: str, reason: str = "logout") -> None:
    payload = decode_token(refresh_token)
    sid = payload.get("sid")
    user_id = payload.get("sub")
    if not sid or not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    session = db.query(UserSession).filter(UserSession.id == sid, UserSession.user_id == user_id).first()
    if not session:
        return

    session.revoked_at = _now()
    session.revoked_reason = reason
    db.commit()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if payload.get("token_type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")

    user_id = payload.get("sub")
    sid = payload.get("sid")
    if not user_id or not sid:
        raise HTTPException(status_code=401, detail="Invalid access token")

    user = db.query(User).filter(User.id == user_id).first()
    session = db.query(UserSession).filter(UserSession.id == sid, UserSession.user_id == user_id).first()
    if not user or not session or session.revoked_at is not None or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if session.expires_at < _now():
        raise HTTPException(status_code=401, detail="Session expired")

    return user


def get_current_root_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.root_admin:
        raise HTTPException(status_code=403, detail="Root admin access required")
    return current_user


def get_client_context(
    x_forwarded_for: Optional[str] = Header(default=None),
    user_agent: Optional[str] = Header(default=None),
) -> tuple[Optional[str], Optional[str]]:
    ip_address = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    return ip_address, user_agent


def bootstrap_root_admin(db: Session) -> None:
    existing_root = db.query(User).filter(User.role == UserRole.root_admin).first()
    if existing_root:
        return

    username = os.getenv("ROOT_ADMIN_USERNAME", "root")
    email = os.getenv("ROOT_ADMIN_EMAIL", "root@local")
    password = os.getenv("ROOT_ADMIN_PASSWORD", "ChangeMeNow!123")

    root_user = User(role=UserRole.root_admin, status=UserStatus.active)
    db.add(root_user)
    db.flush()

    root_identity = UserIdentity(
        user_id=root_user.id,
        provider=AuthProvider.native,
        provider_user_id=username,
        username=username,
        email=email,
        email_verified=True,
    )
    db.add(root_identity)

    root_creds = UserCredential(user_id=root_user.id, password_hash=hash_password(password), must_reset_password=True)
    db.add(root_creds)

    root_profile = Profile(user_id=root_user.id, given_name="Root", family_name="Admin", nick_name="root")
    db.add(root_profile)

    db.commit()

    write_audit_log(
        db,
        actor_user_id=root_user.id,
        action="bootstrap_root_admin",
        target_type="user",
        target_id=root_user.id,
    )
