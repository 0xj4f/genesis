"""Unit tests for JWT signing modes + JKU support.

Self-contained: no MySQL, no running server. Exercises app.config, app.auth.keys and
app.auth.auth directly across the three signing modes (jku | rsa | secret), and guards
the security-sensitive invariants (no silent HS256 fallback, alg-confusion rejected,
issuer never acts on the jku header, backward compatibility with kid-only tokens).

Run just this file:  pytest tests/test_signing_modes.py -v
"""

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

from app.config import Settings
from app.auth import keys as keys_mod
from app.auth.auth import create_access_token, create_refresh_token, decode_token

LEGACY_SECRET = "0f2883258b3c2cb9e21f1bdc827eafb9b7ad5509bf37103f82a1abab9109c65a"


def _header(token: str) -> dict:
    seg = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(seg + "=="))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _forge_hs256(claims: dict, secret: str, kid: str) -> str:
    """Hand-craft an HS256 JWT (raw HMAC), simulating an attacker that does NOT use
    python-jose's guarded encoder (which refuses asymmetric keys as HMAC secrets)."""
    header = {"alg": "HS256", "kid": kid, "typ": "JWT"}
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(claims).encode())}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(sig)}"


def _base_claims(issuer="https://test.local", aud="genesis-api"):
    now = int(time.time())
    return {
        "iss": issuer,
        "aud": [aud],
        "iat": now,
        "nbf": now,
        "exp": now + 300,
        "sub": "attacker",
    }


# ============================================================
# Config layer
# ============================================================

class TestConfig:
    def test_default_mode_is_jku_and_generate(self):
        s = Settings(_env_file=None)
        assert s.OAUTH_SIGNING_MODE == "jku"
        assert s.OAUTH_KEY_SOURCE == "generate"

    def test_signing_algorithm_by_mode(self):
        assert Settings(_env_file=None, OAUTH_SIGNING_MODE="jku").signing_algorithm == "RS256"
        assert Settings(_env_file=None, OAUTH_SIGNING_MODE="rsa").signing_algorithm == "RS256"
        assert Settings(
            _env_file=None, OAUTH_SIGNING_MODE="secret", OAUTH_SECRET_KEY="a-strong-secret-value"
        ).signing_algorithm == "HS256"

    def test_jku_url_defaults_to_issuer_jwks(self):
        s = Settings(_env_file=None, OAUTH_ISSUER="https://auth.example.com")
        assert s.jku_url == "https://auth.example.com/.well-known/jwks.json"

    def test_jku_url_override(self):
        s = Settings(
            _env_file=None,
            OAUTH_ISSUER="https://auth.example.com",
            OAUTH_JKU_URL="https://cdn.example.com/keys.json",
        )
        assert s.jku_url == "https://cdn.example.com/keys.json"

    def test_secret_mode_rejects_empty_secret(self):
        with pytest.raises(Exception):
            Settings(_env_file=None, OAUTH_SIGNING_MODE="secret", OAUTH_SECRET_KEY="")

    def test_secret_mode_rejects_legacy_committed_default(self):
        with pytest.raises(Exception):
            Settings(_env_file=None, OAUTH_SIGNING_MODE="secret", OAUTH_SECRET_KEY=LEGACY_SECRET)

    def test_secret_mode_accepts_strong_secret(self):
        s = Settings(_env_file=None, OAUTH_SIGNING_MODE="secret", OAUTH_SECRET_KEY="strong-unique-secret")
        assert s.OAUTH_SIGNING_MODE == "secret"

    def test_rsa_and_jku_modes_dont_require_secret(self):
        # No secret needed; must not raise.
        assert Settings(_env_file=None, OAUTH_SIGNING_MODE="jku").OAUTH_SECRET_KEY == ""
        assert Settings(_env_file=None, OAUTH_SIGNING_MODE="rsa").OAUTH_SECRET_KEY == ""

    def test_invalid_mode_rejected(self):
        with pytest.raises(Exception):
            Settings(_env_file=None, OAUTH_SIGNING_MODE="jwk")  # typo / not in Literal


# ============================================================
# keys.py — headers, signing key, jwks, verification key
# ============================================================

class TestKeys:
    def test_build_jwt_headers_secret(self, configure):
        configure(mode="secret", secret="strong-secret")
        assert keys_mod.build_jwt_headers("test-kid") == {}

    def test_build_jwt_headers_rsa(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="rsa", priv=priv, pub=pub)
        assert keys_mod.build_jwt_headers("test-kid") == {"kid": "test-kid"}

    def test_build_jwt_headers_jku(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, issuer="https://test.local")
        headers = keys_mod.build_jwt_headers("test-kid")
        assert headers["kid"] == "test-kid"
        assert headers["jku"] == "https://test.local/.well-known/jwks.json"

    def test_get_signing_key_secret(self, configure):
        configure(mode="secret", secret="strong-secret")
        kid, key, alg = keys_mod.get_signing_key()
        assert kid == "" and key == "strong-secret" and alg == "HS256"

    def test_get_signing_key_rsa(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="rsa", priv=priv, pub=pub, kid="test-kid")
        kid, key, alg = keys_mod.get_signing_key()
        assert kid == "test-kid" and alg == "RS256"

    def test_get_signing_key_rsa_missing_raises(self, configure, tmp_path):
        # rsa/jku with no key files must raise (no silent HS256 fallback).
        configure(
            mode="rsa",
            key_source="file",
            priv=str(tmp_path / "missing-priv.pem"),
            pub=str(tmp_path / "missing-pub.pem"),
        )
        with pytest.raises(RuntimeError):
            keys_mod.get_signing_key()

    def test_get_jwks_populated_for_rsa_jku(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid")
        jwks = keys_mod.get_jwks()
        assert len(jwks["keys"]) == 1
        assert jwks["keys"][0]["kid"] == "test-kid"
        assert jwks["keys"][0]["alg"] == "RS256"
        assert jwks["keys"][0]["kty"] == "RSA"

    def test_get_jwks_empty_for_secret(self, configure):
        configure(mode="secret", secret="strong-secret")
        assert keys_mod.get_jwks() == {"keys": []}

    def test_verification_key_known_kid(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="rsa", priv=priv, pub=pub, kid="test-kid")
        result = keys_mod.get_verification_key_by_kid("test-kid")
        assert result is not None
        _, alg = result
        assert alg == "RS256"

    def test_verification_key_unknown_kid_returns_none(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid")
        # Unknown kid must NOT fall back to a symmetric secret.
        assert keys_mod.get_verification_key_by_kid("some-other-kid") is None

    def test_verification_key_secret_mode(self, configure):
        configure(mode="secret", secret="strong-secret")
        key, alg = keys_mod.get_verification_key_by_kid("anything")
        assert key == "strong-secret" and alg == "HS256"


# ============================================================
# keys.py — ensure_keys_available (startup provisioning)
# ============================================================

class TestEnsureKeys:
    def test_generate_creates_key_files(self, configure, tmp_path):
        priv = tmp_path / "gen-priv.pem"
        pub = tmp_path / "gen-pub.pem"
        configure(mode="jku", key_source="generate", priv=str(priv), pub=str(pub), kid="test-kid")
        assert not priv.exists()
        keys_mod.ensure_keys_available()
        assert priv.exists() and pub.exists()
        assert len(keys_mod.get_jwks()["keys"]) == 1

    def test_generate_is_idempotent(self, configure, tmp_path):
        priv = tmp_path / "gen-priv.pem"
        pub = tmp_path / "gen-pub.pem"
        configure(mode="rsa", key_source="generate", priv=str(priv), pub=str(pub), kid="test-kid")
        keys_mod.ensure_keys_available()
        first = priv.read_bytes()
        keys_mod.invalidate_cache()
        keys_mod.ensure_keys_available()  # must NOT regenerate an existing key
        assert priv.read_bytes() == first

    def test_file_mode_missing_keys_raises(self, configure, tmp_path):
        configure(
            mode="jku",
            key_source="file",
            priv=str(tmp_path / "nope-priv.pem"),
            pub=str(tmp_path / "nope-pub.pem"),
        )
        with pytest.raises(RuntimeError):
            keys_mod.ensure_keys_available()

    def test_secret_mode_requires_secret(self, configure):
        configure(mode="secret", secret="")
        with pytest.raises(RuntimeError):
            keys_mod.ensure_keys_available()

    def test_secret_mode_ok_with_secret(self, configure):
        configure(mode="secret", secret="strong-secret")
        keys_mod.ensure_keys_available()  # must not raise


# ============================================================
# auth.py — create/decode round trips per mode
# ============================================================

class TestRoundTrip:
    def _payload(self):
        return {
            "sub": "user-123",
            "username": "alice",
            "email": "alice@example.com",
            "email_verified": False,
            "auth_method": "password",
            "scope": "openid profile email",
            "sid": "sess-1",
        }

    def test_jku_roundtrip(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid", issuer="https://test.local")
        token, jti = create_access_token(self._payload())
        h = _header(token)
        assert h["alg"] == "RS256"
        assert h["kid"] == "test-kid"
        assert h["jku"] == "https://test.local/.well-known/jwks.json"
        decoded = decode_token(token, expected_type="access")
        assert decoded["sub"] == "user-123"
        assert decoded["jti"] == jti

    def test_rsa_roundtrip_no_jku(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="rsa", priv=priv, pub=pub, kid="test-kid")
        token, _ = create_access_token(self._payload())
        h = _header(token)
        assert h["alg"] == "RS256"
        assert h["kid"] == "test-kid"
        assert "jku" not in h
        assert decode_token(token)["sub"] == "user-123"

    def test_secret_roundtrip(self, configure):
        configure(mode="secret", secret="strong-secret")
        token, _ = create_access_token(self._payload())
        h = _header(token)
        assert h["alg"] == "HS256"
        assert "kid" not in h
        assert "jku" not in h
        assert decode_token(token)["sub"] == "user-123"

    def test_refresh_token_type_and_rejection(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid")
        refresh, _ = create_refresh_token(self._payload())
        # Valid as a refresh token
        assert decode_token(refresh, expected_type="refresh")["token_type"] == "refresh"
        # But must be rejected where an access token is expected
        with pytest.raises(HTTPException) as exc:
            decode_token(refresh, expected_type="access")
        assert exc.value.status_code == 401


# ============================================================
# Security & backward-compat invariants
# ============================================================

class TestSecurity:
    def test_backward_compat_kid_only_token_validates_in_jku_mode(self, configure, rsa_key_files):
        """A token minted before jku existed (kid only, no jku) still validates in jku mode."""
        priv, pub = rsa_key_files
        # Mint in rsa mode (no jku header).
        configure(mode="rsa", priv=priv, pub=pub, kid="test-kid")
        token, _ = create_access_token({"sub": "user-9", "sid": "s"})
        assert "jku" not in _header(token)
        # Switch to jku mode (same keys/kid) and decode — must still work.
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid")
        assert decode_token(token)["sub"] == "user-9"

    def test_decode_ignores_jku_header(self, configure, rsa_key_files):
        """The issuer never acts on the jku header: a bogus jku must not affect validation."""
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid", issuer="https://test.local")
        kid, key, alg = keys_mod.get_signing_key()
        now = int(time.time())
        claims = {
            "iss": "https://test.local",
            "aud": ["genesis-api"],
            "iat": now,
            "nbf": now,
            "exp": now + 300,
            "sub": "user-x",
        }
        # Validly signed, but with an attacker-controlled jku pointing elsewhere.
        token = jose_jwt.encode(
            claims, key, algorithm=alg,
            headers={"kid": kid, "jku": "http://evil.example/keys.json"},
        )
        # decode_token uses local kid lookup and ignores jku → still valid.
        assert decode_token(token)["sub"] == "user-x"

    def test_alg_confusion_rejected(self, configure, rsa_key_files):
        """Classic RS256->HS256 confusion: forge HS256 using the RSA public key as the
        HMAC secret and the real kid. Must be rejected because verification is pinned to
        the key store's algorithm (RS256)."""
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid", issuer="https://test.local")
        public_pem = open(pub).read()
        forged = _forge_hs256(_base_claims(), public_pem, "test-kid")
        # Sanity: the forged token really is HS256 with the real kid.
        assert _header(forged)["alg"] == "HS256"
        with pytest.raises(HTTPException) as exc:
            decode_token(forged)
        assert exc.value.status_code == 401

    def test_tampered_payload_rejected(self, configure, rsa_key_files):
        priv, pub = rsa_key_files
        configure(mode="jku", priv=priv, pub=pub, kid="test-kid", issuer="https://test.local")
        token, _ = create_access_token({"sub": "user-1", "sid": "s"})
        head, payload, sig = token.split(".")
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps({**json.loads(base64.urlsafe_b64decode(payload + "==")), "sub": "admin"}).encode()
        ).rstrip(b"=").decode()
        tampered = f"{head}.{tampered_payload}.{sig}"
        with pytest.raises(HTTPException):
            decode_token(tampered)
