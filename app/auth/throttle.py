"""Per-account throttling for password, current-password and client-secret checks."""

import hashlib

from fastapi import HTTPException

from app.config import get_settings
from app.utils.audit import security_event
from app.utils.security_store import get_security_store

settings = get_settings()


def login_key(username: str) -> str:
    # Keyed by the submitted name so unknown usernames are throttled exactly
    # like real ones and lockouts do not reveal which accounts exist.
    return "user:" + hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()


def client_key(client_id: str) -> str:
    return "client:" + client_id


def ensure_attempt_allowed(key: str) -> None:
    retry = get_security_store().login_retry_after(key)
    if retry:
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again later.",
            headers={"Retry-After": str(retry)},
        )


def record_failure(key: str) -> None:
    locked_for = get_security_store().record_login_failure(
        key,
        settings.LOGIN_MAX_FAILURES,
        settings.LOGIN_FAILURE_WINDOW_SECONDS,
        settings.LOGIN_LOCKOUT_MAX_SECONDS,
    )
    if locked_for:
        security_event("account_locked", key=key[:24], seconds=locked_for)


def record_success(key: str) -> None:
    get_security_store().clear_login_failures(key)
