"""Shared fixtures for the self-contained (no DB / no server) unit tests.

These fixtures mutate the process-wide Settings singleton returned by get_settings()
(the same object referenced by app.auth.keys.settings and app.auth.auth.settings) and
invalidate the key cache between configurations. monkeypatch restores every attribute
after each test, so mode changes never leak between tests.
"""

import pytest


@pytest.fixture(scope="session")
def rsa_key_files(tmp_path_factory):
    """Generate one RSA key pair for the whole session and write it to a temp dir.

    Returns (private_path, public_path). Reused across tests so we don't pay RSA
    key-gen cost per test.
    """
    from app.auth.keys import generate_rsa_key_pair

    d = tmp_path_factory.mktemp("rsa_keys")
    priv = d / "dev-private.pem"
    pub = d / "dev-public.pem"
    priv_pem, pub_pem = generate_rsa_key_pair()
    priv.write_bytes(priv_pem)
    pub.write_bytes(pub_pem)
    return str(priv), str(pub)


@pytest.fixture
def configure(monkeypatch):
    """Configure the shared Settings for a signing mode; auto-restores after the test.

    Usage: settings = configure(mode="jku", priv=..., pub=...)
    """
    from app.config import get_settings
    from app.auth import keys as keys_mod

    s = get_settings()

    def _apply(
        *,
        mode,
        key_source="file",
        secret="",
        priv=None,
        pub=None,
        kid="test-kid",
        issuer="https://test.local",
        jku_url=None,
        audience="genesis-api",
    ):
        monkeypatch.setattr(s, "OAUTH_SIGNING_MODE", mode)
        monkeypatch.setattr(s, "OAUTH_KEY_SOURCE", key_source)
        monkeypatch.setattr(s, "OAUTH_SECRET_KEY", secret)
        monkeypatch.setattr(s, "OAUTH_JWT_KID", kid)
        monkeypatch.setattr(s, "OAUTH_ISSUER", issuer)
        monkeypatch.setattr(s, "OAUTH_JKU_URL", jku_url)
        monkeypatch.setattr(s, "OAUTH_DEFAULT_AUDIENCE", audience)
        if priv is not None:
            monkeypatch.setattr(s, "OAUTH_PRIVATE_KEY_PATH", priv)
        if pub is not None:
            monkeypatch.setattr(s, "OAUTH_PUBLIC_KEY_PATH", pub)
        keys_mod.invalidate_cache()
        return s

    yield _apply
    keys_mod.invalidate_cache()
