import time
import base64
from typing import Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from app.config import get_settings

settings = get_settings()

_key_cache: dict = {}
_cache_timestamp: float = 0.0


def _load_private_key_from_file(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key_from_file(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def generate_rsa_key_pair(key_size: int = 2048) -> tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _int_to_base64url(n: int) -> str:
    byte_length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(byte_length, byteorder="big")).rstrip(b"=").decode("ascii")


def public_key_to_jwk(public_key, kid: str, alg: str = "RS256") -> dict:
    public_numbers = public_key.public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": alg,
        "kid": kid,
        "n": _int_to_base64url(public_numbers.n),
        "e": _int_to_base64url(public_numbers.e),
    }


def _load_keys():
    global _key_cache, _cache_timestamp

    now = time.time()
    if _key_cache and (now - _cache_timestamp) < settings.JWKS_CACHE_TTL_SECONDS:
        return _key_cache

    keys = {}

    # Try file-based keys
    if settings.OAUTH_PRIVATE_KEY_PATH and settings.OAUTH_PUBLIC_KEY_PATH:
        try:
            private_key = _load_private_key_from_file(settings.OAUTH_PRIVATE_KEY_PATH)
            public_key = _load_public_key_from_file(settings.OAUTH_PUBLIC_KEY_PATH)
            kid = settings.OAUTH_JWT_KID
            keys[kid] = {
                "kid": kid,
                "algorithm": "RS256",
                "private_key": private_key,
                "public_key": public_key,
                "is_current": True,
            }
        except FileNotFoundError:
            pass

    _key_cache = keys
    _cache_timestamp = now
    return keys


def get_signing_key() -> tuple[str, object, str]:
    """Returns (kid, private_key, algorithm) for the current signing key."""
    keys = _load_keys()

    # Find the current signing key (RS256)
    for kid, key_info in keys.items():
        if key_info.get("is_current"):
            return kid, key_info["private_key"], key_info["algorithm"]

    # Fallback to HS256 with shared secret
    return "", settings.OAUTH_SECRET_KEY, "HS256"


def get_verification_keys() -> dict:
    """Returns dict of kid -> {public_key, algorithm} for all active keys."""
    keys = _load_keys()
    result = {}
    for kid, key_info in keys.items():
        result[kid] = {
            "public_key": key_info["public_key"],
            "algorithm": key_info["algorithm"],
        }
    return result


def get_verification_key_by_kid(kid: str) -> Optional[tuple[object, str]]:
    """Returns (key, algorithm) for a specific kid. Returns None if not found."""
    keys = get_verification_keys()
    if kid in keys:
        return keys[kid]["public_key"], keys[kid]["algorithm"]

    # Fallback: if no kid match and we're using HS256
    if not keys:
        return settings.OAUTH_SECRET_KEY, "HS256"

    return None


def get_jwks() -> dict:
    """Returns the JWKS document (RFC 7517) for the /.well-known/jwks.json endpoint."""
    keys = _load_keys()
    jwk_list = []
    for kid, key_info in keys.items():
        jwk = public_key_to_jwk(key_info["public_key"], kid, key_info["algorithm"])
        jwk_list.append(jwk)
    return {"keys": jwk_list}


def invalidate_cache():
    """Force reload keys on next access."""
    global _key_cache, _cache_timestamp
    _key_cache = {}
    _cache_timestamp = 0.0
