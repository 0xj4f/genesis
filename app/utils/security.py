"""Password and OAuth client-secret hashing.

New passwords are hashed with Argon2id through pwdlib. Hashes written before the
migration (bcrypt) still verify, and verify_and_update_password returns an
Argon2id replacement so callers can upgrade them on the next successful login.
"""

import hashlib
import hmac
import secrets
import threading
from contextlib import contextmanager
from functools import lru_cache

from fastapi import HTTPException
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.config import get_settings

settings = get_settings()

_argon2 = Argon2Hasher(
    memory_cost=settings.PASSWORD_ARGON2_MEMORY_KIB,
    time_cost=settings.PASSWORD_ARGON2_TIME_COST,
    parallelism=settings.PASSWORD_ARGON2_PARALLELISM,
)
_bcrypt = BcryptHasher()
# The first hasher writes new hashes; the others are only used to verify.
_password_hash = PasswordHash(
    (_argon2, _bcrypt) if settings.PASSWORD_HASH_SCHEME == "argon2id" else (_bcrypt, _argon2)
)

# Argon2id holds its memory cost for every hash in flight. Bound concurrency so
# a burst of logins cannot exhaust the container's memory limit.
_hash_slots = threading.BoundedSemaphore(settings.PASSWORD_HASH_CONCURRENCY)
_HASH_SLOT_TIMEOUT_SECONDS = 10

BCRYPT_MAX_BYTES = 72
CLIENT_SECRET_PREFIX = "sha256$"


@contextmanager
def _hash_slot():
    if not _hash_slots.acquire(timeout=_HASH_SLOT_TIMEOUT_SECONDS):
        raise HTTPException(status_code=503, detail="Server busy, please retry", headers={"Retry-After": "5"})
    try:
        yield
    finally:
        _hash_slots.release()


def hash_password(password: str) -> str:
    """Hash a password with the configured scheme (Argon2id by default)."""
    if settings.PASSWORD_HASH_SCHEME == "bcrypt" and len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError("Password must be at most 72 UTF-8 bytes while PASSWORD_HASH_SCHEME=bcrypt")
    with _hash_slot():
        return _password_hash.hash(password)


def verify_and_update_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Verify a password. Returns (valid, new_hash), where new_hash is set when
    the stored hash uses an outdated algorithm or parameters."""
    try:
        with _hash_slot():
            return _password_hash.verify_and_update(plain_password, hashed_password)
    except (UnknownHashError, ValueError, TypeError):
        # Unknown/corrupt hash, or a >72-byte password checked against bcrypt.
        return False, None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return verify_and_update_password(plain_password, hashed_password)[0]


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(32))


def verify_dummy_password(plain_password: str) -> None:
    """Spend the same work as a real verification when the account is unknown
    or has no password, so response time does not reveal which usernames exist."""
    verify_password(plain_password, _dummy_hash())


# ---- OAuth client secrets ----
# Client secrets are 256-bit random values, so a slow password hash adds cost
# without adding security. SHA-256 with a constant-time compare is sufficient.

def hash_client_secret(secret: str) -> str:
    return CLIENT_SECRET_PREFIX + hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_client_secret(secret: str, stored_hash: str) -> tuple[bool, str | None]:
    """Returns (valid, upgraded_hash). Legacy bcrypt client hashes verify once
    and return a SHA-256 replacement for the caller to store."""
    if not secret or not stored_hash:
        return False, None
    if stored_hash.startswith(CLIENT_SECRET_PREFIX):
        return hmac.compare_digest(hash_client_secret(secret), stored_hash), None
    if verify_password(secret, stored_hash):
        return True, hash_client_secret(secret)
    return False, None
