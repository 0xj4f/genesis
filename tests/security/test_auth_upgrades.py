"""Tests for the 2026-10 auth hardening: Argon2id/pwdlib, per-account throttling,
re-authentication, admin policy, client-bound refresh tokens, consent, optional
email verification, and the Authlib SSO client with the web-app hand-off."""

import hashlib
import inspect
import re
import threading
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError

from app.auth import auth as auth_module
from app.auth import keys as keys_module
from app.auth import throttle
from app.auth.auth import decode_token, require_role
from app.auth.policy import can_assign_role, can_manage
from app.config import Settings, get_settings
from app.models.email_verification_db_model import EmailVerificationToken
from app.models.oauth_account_db_model import OAuthAccount
from app.models.oauth_client_db_model import OAuthClient
from app.models.session_db_model import Session as LoginSession
from app.models.user_db_model import User as UserModel
from app.routes import oidc as oidc_routes
from app.services import oidc_service, sso_service, verification_service
from app.utils import security as security_module
from app.utils.security import (
    hash_client_secret,
    hash_password,
    verify_client_secret,
    verify_password,
)

PASSWORD = "ValidPassword123!"
settings = get_settings()


def bearer(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture(autouse=True)
def shared_store(store, monkeypatch):
    """Use the test's clock-controlled store for throttling, SSO and resend state too."""
    for module in (throttle, sso_service, verification_service):
        monkeypatch.setattr(module, "get_security_store", lambda: store)
    # Per-IP limits are covered elsewhere; keep them out of the way here.
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_PER_MINUTE", 1000)
    monkeypatch.setattr(settings, "REFRESH_RATE_LIMIT_PER_MINUTE", 1000)
    return store


# ---- Passwords: Argon2id, salts, upgrade, timing, concurrency ----

def test_new_passwords_use_argon2id_with_unique_salts():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert first != second  # fresh random salt per hash
    assert verify_password(PASSWORD, first) and verify_password(PASSWORD, second)
    assert not verify_password("WrongPassword123!", first)


def test_bcrypt_hash_is_upgraded_to_argon2id_on_login(client, make_user, login, db):
    user = make_user()
    assert user.password.startswith("$2b$")
    login(user)
    db.refresh(user)
    assert user.password.startswith("$argon2id$")
    login(user)  # the upgraded hash still verifies


def test_long_password_against_bcrypt_hash_fails_cleanly(make_user):
    user = make_user()
    assert not verify_password("A1!" + "x" * 100, user.password)


def test_unknown_user_still_spends_hashing_work(client, monkeypatch):
    calls = []
    monkeypatch.setattr(auth_module, "verify_dummy_password", calls.append)
    response = client.post("/token", data={"username": "nobody-here", "password": PASSWORD})
    assert response.status_code == 401
    assert calls == [PASSWORD]


def test_hash_concurrency_is_bounded(monkeypatch):
    slots = threading.BoundedSemaphore(1)
    slots.acquire()
    monkeypatch.setattr(security_module, "_hash_slots", slots)
    monkeypatch.setattr(security_module, "_HASH_SLOT_TIMEOUT_SECONDS", 0.01)
    with pytest.raises(HTTPException) as error:
        hash_password(PASSWORD)
    assert error.value.status_code == 503


# ---- Per-account throttling ----

def test_account_locks_after_repeated_failures(client, make_user, clock):
    user = make_user()
    for _ in range(settings.LOGIN_MAX_FAILURES):
        assert client.post("/token", data={"username": user.username, "password": "Wrong-pass-123!"}).status_code == 401
    locked = client.post("/token", data={"username": user.username, "password": PASSWORD})
    assert locked.status_code == 429
    assert "failed attempts" in locked.json()["detail"]
    assert int(locked.headers["Retry-After"]) > 0
    clock[0] += 61
    assert client.post("/token", data={"username": user.username, "password": PASSWORD}).status_code == 200


def test_unknown_usernames_lock_the_same_way(client):
    for _ in range(settings.LOGIN_MAX_FAILURES):
        assert client.post("/token", data={"username": "ghost-user", "password": "Wrong-pass-123!"}).status_code == 401
    assert client.post("/token", data={"username": "Ghost-User", "password": "Wrong-pass-123!"}).status_code == 429


def test_repeated_lockouts_back_off(store, clock):
    key = throttle.login_key("someone")
    lengths = []
    for _ in range(3):
        for _ in range(settings.LOGIN_MAX_FAILURES):
            locked_for = store.record_login_failure(key, settings.LOGIN_MAX_FAILURES, 900, 900)
        lengths.append(locked_for)
        clock[0] += locked_for + 1
    assert lengths == [60, 120, 240]


# ---- Re-authentication (F2) ----

def test_email_change_requires_current_password(client, make_user, login):
    user = make_user()
    headers = bearer(login(user))
    path = f"/users/{user.id}"
    assert client.put(path, headers=headers, json={"email": "new@example.com"}).status_code == 400
    assert client.put(path, headers=headers, json={"email": "new@example.com", "current_password": "Wrong-pass-123!"}).status_code == 400
    response = client.put(path, headers=headers, json={"email": "new@example.com", "current_password": PASSWORD})
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "new@example.com"
    # Username-only changes do not need the password.
    assert client.put(path, headers=headers, json={"username": user.username}).status_code == 200


def test_password_change_needs_correct_current_password(client, make_user, login):
    user = make_user()
    headers = bearer(login(user))
    body = {"current_password": "Wrong-pass-123!", "new_password": "ChangedPassword123!"}
    assert client.post("/users/me/password", headers=headers, json=body).status_code == 400
    assert client.post("/users/me/password", headers=headers, json={"new_password": "ChangedPassword123!"}).status_code == 400
    assert client.post("/users/me/password", headers=headers, json={**body, "new_password": "short"}).status_code == 422


def test_sso_only_account_needs_recent_sign_in_to_set_password(client, make_user, login, db):
    user = make_user()
    tokens = login(user)
    user.password = None  # behave like an SSO-only account
    db.commit()
    body = {"new_password": "FirstPassword123!"}
    session = db.get(LoginSession, decode_token(tokens["access_token"])["sid"])
    session.created_at = datetime.utcnow() - timedelta(hours=1)
    db.commit()
    assert client.post("/users/me/password", headers=bearer(tokens), json=body).status_code == 403
    session.created_at = datetime.utcnow()
    db.commit()
    assert client.post("/users/me/password", headers=bearer(tokens), json=body).status_code == 200


# ---- Admin policy (F9) ----

def _actor(role, ident):
    return SimpleNamespace(id=ident, role=role)


def test_can_manage_matrix():
    user, user2 = _actor("user", "u1"), _actor("user", "u2")
    admin, admin2 = _actor("admin", "a1"), _actor("admin", "a2")
    root, root2 = _actor("root", "r1"), _actor("root", "r2")
    assert can_manage(user, user) and not can_manage(user, user2) and not can_manage(user, admin)
    assert can_manage(admin, user) and can_manage(admin, admin)
    assert not can_manage(admin, admin2) and not can_manage(admin, root)
    assert can_manage(root, user) and can_manage(root, admin) and can_manage(root, root)
    assert not can_manage(root, root2)


def test_role_assignment_matrix():
    user, admin, root = _actor("user", "u1"), _actor("admin", "a1"), _actor("root", "r1")
    assert can_assign_role(root, user, "admin") and can_assign_role(root, admin, "user")
    assert not can_assign_role(admin, user, "admin") and not can_assign_role(admin, user, "root")
    assert not can_assign_role(root, root, "user")  # no self role changes
    assert not can_assign_role(admin, admin, "root")
    assert not can_assign_role(root, user, "superuser")


def test_admins_cannot_manage_other_admins(client, make_user, login):
    admin, other_admin, regular = make_user(role="admin"), make_user(role="admin"), make_user()
    headers = bearer(login(admin))
    target = other_admin.id
    assert client.put(f"/users/{target}", headers=headers, json={"username": "renamed"}).status_code == 403
    assert client.delete(f"/users/{target}", headers=headers).status_code == 403
    assert client.post(f"/admin/users/{target}/disable", headers=headers).status_code == 403
    assert client.post(f"/admin/users/{target}/role", headers=headers, json={"role": "user"}).status_code == 403
    assert client.post(f"/admin/users/{target}/password", headers=headers, json={"new_password": "ResetPassword123!"}).status_code == 403
    assert client.delete(f"/admin/users/{target}", headers=headers).status_code == 403
    # Admins still manage regular users, but cannot promote them.
    assert client.post(f"/admin/users/{regular.id}/role", headers=headers, json={"role": "admin"}).status_code == 403
    assert client.post(f"/admin/users/{regular.id}/password", headers=headers, json={"new_password": "ResetPassword123!"}).status_code == 200


def test_root_manages_admins_and_role_change_signs_user_out(client, make_user, login):
    root, admin, regular = make_user(role="root"), make_user(role="admin"), make_user()
    root_headers = bearer(login(root))
    regular_tokens = login(regular)
    assert client.post(f"/admin/users/{regular.id}/role", headers=root_headers, json={"role": "admin"}).status_code == 200
    # The old token carried role=user; the user must sign in again.
    assert client.get("/users/me/", headers=bearer(regular_tokens)).status_code == 401
    assert decode_token(login(regular)["access_token"])["role"] == "admin"
    assert client.post(f"/admin/users/{admin.id}/password", headers=root_headers, json={"new_password": "ResetPassword123!"}).status_code == 200
    assert client.post(f"/admin/users/{root.id}/role", headers=root_headers, json={"role": "user"}).status_code == 403


def test_disabling_a_user_revokes_their_sessions(client, make_user, login):
    admin, regular = make_user(role="admin"), make_user()
    regular_tokens = login(regular)
    assert client.post(f"/admin/users/{regular.id}/disable", headers=bearer(login(admin))).status_code == 200
    assert client.post("/refresh_token", headers={"Authorization": f"Bearer {regular_tokens['refresh_token']}"}).status_code in (401, 403)


# ---- OAuth clients: secrets, client-bound refresh (F4), consent (F13) ----

CLIENT_SECRET = "client-secret-value-for-tests-0123456789"
REDIRECT = "https://app.example/callback"


def _make_client(db, *, first_party=True, secret_hash=None, grant_types=None):
    client = OAuthClient(
        client_secret_hash=secret_hash or hash_client_secret(CLIENT_SECRET),
        client_name=f"client-{time.monotonic_ns()}",
        redirect_uris=[REDIRECT],
        allowed_scopes=["openid", "profile", "email", "offline_access"],
        allowed_audiences=["genesis-api"],
        grant_types=grant_types or ["authorization_code", "refresh_token", "client_credentials"],
        is_active=True,
        is_confidential=True,
        is_first_party=first_party,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_client_secrets_use_sha256_and_legacy_bcrypt_upgrades(db):
    assert hash_client_secret(CLIENT_SECRET).startswith("sha256$")
    assert verify_client_secret(CLIENT_SECRET, hash_client_secret(CLIENT_SECRET)) == (True, None)
    import bcrypt
    legacy = _make_client(db, secret_hash=bcrypt.hashpw(CLIENT_SECRET.encode(), bcrypt.gensalt(rounds=4)).decode())
    with pytest.raises(HTTPException):
        oidc_service.authenticate_client(db, legacy, "wrong-secret")
    oidc_service.authenticate_client(db, legacy, CLIENT_SECRET)
    db.refresh(legacy)
    assert legacy.client_secret_hash == hash_client_secret(CLIENT_SECRET)


def _authorize(client, headers, oauth_client, scope="openid offline_access"):
    response = client.get("/oauth/authorize", headers=headers, follow_redirects=False, params={
        "response_type": "code", "client_id": oauth_client.id, "redirect_uri": REDIRECT,
        "scope": scope, "state": "state-123",
    })
    assert response.status_code == 302, response.text
    return parse_qs(urlsplit(response.headers["location"]).query)["code"][0]


def _exchange(client, oauth_client, code):
    response = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
        "client_id": oauth_client.id, "client_secret": CLIENT_SECRET,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_oidc_refresh_tokens_are_bound_to_their_client(client, make_user, login, db):
    user = make_user()
    first_party_tokens = login(user)
    oauth_client, other_client = _make_client(db), _make_client(db)
    tokens = _exchange(client, oauth_client, _authorize(client, bearer(first_party_tokens), oauth_client))
    claims = decode_token(tokens["access_token"])
    assert claims["client_id"] == oauth_client.id and claims["role"] == "user"
    assert oauth_client.id in claims["aud"]

    refresh = tokens["refresh_token"]
    assert client.post("/refresh_token", headers={"Authorization": f"Bearer {refresh}"}).status_code == 400
    grant = {"grant_type": "refresh_token", "refresh_token": refresh}
    assert client.post("/oauth/token", data={**grant, "client_id": other_client.id, "client_secret": CLIENT_SECRET}).status_code == 400
    assert client.post("/oauth/token", data={**grant, "client_id": oauth_client.id}).status_code == 401
    rotated = client.post("/oauth/token", data={**grant, "client_id": oauth_client.id, "client_secret": CLIENT_SECRET})
    assert rotated.status_code == 200, rotated.text
    rotated_claims = decode_token(rotated.json()["access_token"])
    assert rotated_claims["client_id"] == oauth_client.id and oauth_client.id in rotated_claims["aud"]

    # First-party refresh tokens are not accepted at the OAuth token endpoint.
    first_party_grant = {"grant_type": "refresh_token", "refresh_token": first_party_tokens["refresh_token"]}
    assert client.post("/oauth/token", data={**first_party_grant, "client_id": oauth_client.id, "client_secret": CLIENT_SECRET}).status_code == 400


def test_refresh_token_only_issued_when_client_allows_it(client, make_user, login, db):
    oauth_client = _make_client(db, grant_types=["authorization_code"])
    tokens = _exchange(client, oauth_client, _authorize(client, bearer(login(make_user())), oauth_client))
    assert "refresh_token" not in tokens


def test_third_party_clients_need_consent(client, make_user, login, db):
    headers = bearer(login(make_user()))
    oauth_client = _make_client(db, first_party=False)
    params = {"response_type": "code", "client_id": oauth_client.id, "redirect_uri": REDIRECT, "scope": "openid", "state": "s1"}
    blocked = client.get("/oauth/authorize", headers=headers, params=params, follow_redirects=False)
    assert blocked.status_code == 403 and blocked.json()["detail"] == "consent_required"

    info = client.get(f"/oauth/clients/{oauth_client.id}/public").json()
    assert info["client_name"] == oauth_client.client_name and "client_secret_hash" not in info

    approved = client.post("/oauth/authorize", headers=headers, json={**params, "consent": "approve"})
    assert approved.status_code == 200
    query = parse_qs(urlsplit(approved.json()["redirect_to"]).query)
    assert query["state"] == ["s1"] and query["code"]
    denied = client.post("/oauth/authorize", headers=headers, json={**params, "consent": "deny"})
    assert parse_qs(urlsplit(denied.json()["redirect_to"]).query)["error"] == ["access_denied"]
    # The redirect target is still validated against the client's registration.
    assert client.post("/oauth/authorize", headers=headers, json={**params, "redirect_uri": "https://evil.example/cb", "consent": "approve"}).status_code == 400


def test_blocking_work_is_not_in_async_handlers():
    assert not inspect.iscoroutinefunction(oidc_routes.token_endpoint)
    dependency = require_role("admin")
    assert not inspect.iscoroutinefunction(dependency)


# ---- Signing keys (F8) ----

def test_signing_requires_explicit_keys_or_strong_dev_secret(monkeypatch, tmp_path):
    def configure(**changes):
        monkeypatch.setattr(keys_module, "settings", keys_module.settings.model_copy(update=changes))
        keys_module.invalidate_cache()

    configure(ENVIRONMENT="development", OAUTH_PRIVATE_KEY_PATH=str(tmp_path / "missing.pem"), OAUTH_PUBLIC_KEY_PATH=str(tmp_path / "missing.pub"))
    with pytest.raises(FileNotFoundError):
        keys_module.get_signing_key()

    configure(OAUTH_PRIVATE_KEY_PATH=None, OAUTH_PUBLIC_KEY_PATH=None, OAUTH_SECRET_KEY=None)
    with pytest.raises(RuntimeError):
        keys_module.get_signing_key()

    configure(OAUTH_SECRET_KEY=SecretStr("too-short"))
    with pytest.raises(RuntimeError):
        keys_module.get_signing_key()

    leaked = "a-secret-that-was-committed-to-git-history"
    monkeypatch.setattr(keys_module, "_LEGACY_SECRET_SHA256", hashlib.sha256(leaked.encode()).hexdigest())
    configure(OAUTH_SECRET_KEY=SecretStr(leaked))
    with pytest.raises(RuntimeError):
        keys_module.get_signing_key()

    configure(OAUTH_SECRET_KEY=SecretStr("a-unique-development-secret-of-enough-length"))
    assert keys_module.get_signing_key()[2] == "HS256"
    configure(ENVIRONMENT="production")
    with pytest.raises(RuntimeError):
        keys_module.get_signing_key()
    keys_module.invalidate_cache()


# ---- Optional email verification ----

@pytest.fixture
def mailbox(monkeypatch):
    sent = []
    monkeypatch.setattr(settings, "EMAIL_VERIFY", True)
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:5173")
    monkeypatch.setattr(settings, "EMAIL_FROM", "genesis@example.com")
    monkeypatch.setattr(verification_service, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def _token_from(mail):
    return re.search(r"#token=([A-Za-z0-9_-]+)", mail[2]).group(1)


def test_email_verification_disabled_by_default(client):
    assert client.get("/auth/config").json()["email_verification"] is False
    data = {"username": "no_mail_user", "email": "nomail@example.com", "password": PASSWORD}
    assert client.post("/users/", json=data).status_code == 200
    assert client.post("/token", data={"username": data["username"], "password": PASSWORD}).status_code == 200


def test_email_verification_gates_password_login(client, mailbox):
    data = {"username": "verify_me", "email": "verify@example.com", "password": PASSWORD}
    assert client.post("/users/", json=data).status_code == 200
    assert client.get("/auth/config").json()["email_verification"] is True
    assert len(mailbox) == 1 and mailbox[0][0] == data["email"]
    login = {"username": data["username"], "password": PASSWORD}
    blocked = client.post("/token", data=login)
    assert blocked.status_code == 403 and blocked.json()["detail"] == "Email address not verified"

    token = _token_from(mailbox[0])
    assert client.post("/auth/email/verify", json={"token": token}).status_code == 200
    assert client.post("/auth/email/verify", json={"token": token}).status_code == 400  # single use
    assert client.post("/token", data=login).status_code == 200


def test_verification_links_expire_and_follow_the_current_email(client, mailbox, make_user, db):
    user = make_user()
    verification_service.send_verification_email(db, user)
    db.query(EmailVerificationToken).update({"expires_at": datetime.utcnow() - timedelta(seconds=1)})
    db.commit()
    assert client.post("/auth/email/verify", json={"token": _token_from(mailbox[-1])}).status_code == 400

    verification_service.send_verification_email(db, user)
    user.email = "changed@example.com"
    db.commit()
    assert client.post("/auth/email/verify", json={"token": _token_from(mailbox[-1])}).status_code == 400


def test_email_change_waits_for_the_new_address(client, mailbox, make_user, login, db):
    user = make_user(email_verified=True)
    headers = bearer(login(user))
    old_email = user.email
    response = client.put(f"/users/{user.id}", headers=headers, json={"email": "next@example.com", "current_password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["email"] == old_email and response.json()["email_change_pending"] is True
    assert mailbox[-1][0] == "next@example.com"
    assert client.post("/auth/email/verify", json={"token": _token_from(mailbox[-1])}).status_code == 200
    db.refresh(user)
    assert user.email == "next@example.com" and user.email_verified is True


def test_resend_never_reveals_accounts(client, mailbox, make_user):
    unverified = make_user(email_verified=False)
    for email in ("nobody@example.com", unverified.email):
        response = client.post("/auth/email/resend", json={"email": email})
        assert response.status_code == 202
        assert response.json()["message"].startswith("If this address")
    assert [mail[0] for mail in mailbox] == [unverified.email]


def test_email_settings_are_validated():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, EMAIL_VERIFY=True)  # needs FRONTEND_URL and EMAIL_FROM
    production = dict(
        _env_file=None, ENVIRONMENT="production", OAUTH_PRIVATE_KEY_PATH="p.pem", OAUTH_PUBLIC_KEY_PATH="k.pem",
        OAUTH_ISSUER="https://auth.example", CORS_ALLOW_ORIGINS="https://app.example", ALLOWED_HOSTS="auth.example",
    )
    email = dict(EMAIL_VERIFY=True, FRONTEND_URL="https://app.example", EMAIL_FROM="genesis@example.com")
    with pytest.raises(ValidationError):
        Settings(**production, **email, EMAIL_BACKEND="console")
    with pytest.raises(ValidationError):
        Settings(**production, **email, EMAIL_BACKEND="smtp", SMTP_HOST="smtp.example", SMTP_SECURITY="none")
    with pytest.raises(ValidationError):
        Settings(**production, FRONTEND_URL="http://app.example")
    assert Settings(**production, **email, EMAIL_BACKEND="smtp", SMTP_HOST="smtp.example").EMAIL_VERIFY


# ---- SSO on Authlib: PKCE, nonce, ID token, hand-off ----

GOOGLE = SimpleNamespace(
    name="google", client_id="google-client-id", client_secret="google-secret",
    authorize_url="https://accounts.example/auth", token_url="https://accounts.example/token",
    userinfo_url="https://accounts.example/userinfo", scopes=["openid", "email", "profile"],
    redirect_uri="https://auth.example/auth/sso/google/callback", pkce=True, oidc=True,
    jwks_uri="https://accounts.example/jwks", issuers=("https://accounts.google.com",),
    field_map={"sub": "sub", "email": "email", "name": "name", "picture": "picture"},
)
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _id_token(nonce_value, **overrides):
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com", "aud": GOOGLE.client_id, "sub": "google-user-1",
        "email": "sso-user@example.com", "email_verified": True, "name": "Sso User",
        "iat": now, "exp": now + 300, "nonce": nonce_value, **overrides,
    }
    return jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "k1"})


@pytest.fixture
def google(monkeypatch):
    monkeypatch.setattr(sso_service, "get_provider", lambda name: GOOGLE)
    monkeypatch.setitem(
        sso_service._jwks_clients, GOOGLE.jwks_uri,
        SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=SIGNING_KEY.public_key())),
    )
    calls = {}

    async def fake_fetch_token(self, url, **kwargs):
        calls.update(kwargs, url=url)
        return {"access_token": "provider-access-token", "id_token": _id_token(calls["nonce"])}

    monkeypatch.setattr(sso_service.AsyncOAuth2Client, "fetch_token", fake_fetch_token)
    return calls


def _start_login(client, google_calls):
    response = client.get("/auth/sso/google/authorize", follow_redirects=False)
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    google_calls["nonce"] = query["nonce"][0]
    return query


def test_google_sign_in_uses_pkce_and_verified_id_token(client, google, db):
    query = _start_login(client, google)
    response = client.get("/auth/sso/google/callback", params={"code": "auth-code", "state": query["state"][0]})
    assert response.status_code == 200, response.text
    assert set(response.json()) >= {"access_token", "refresh_token"}
    # The verifier sent at exchange time matches the challenge sent to the provider.
    assert create_s256_code_challenge(google["code_verifier"]) == query["code_challenge"][0]
    assert decode_token(response.json()["access_token"])["role"] == "user"
    user = db.query(UserModel).filter(UserModel.email == "sso-user@example.com").one()
    assert user.email_verified is True
    account = db.query(OAuthAccount).filter(OAuthAccount.user_id == user.id).one()
    # Provider tokens and raw profiles are no longer stored (F6).
    assert account.access_token is None and account.refresh_token is None and account.raw_userinfo is None


@pytest.mark.parametrize("overrides", [{"aud": "someone-else"}, {"nonce": "replayed"}, {"iss": "https://evil.example"}, {"exp": int(time.time()) - 10}])
def test_invalid_google_id_tokens_are_rejected(overrides):
    with pytest.raises(HTTPException) as error:
        sso_service.verify_id_token(GOOGLE, _id_token("expected-nonce", **overrides), "expected-nonce")
    assert error.value.status_code == 502


def test_sso_hands_off_to_web_app_with_browser_bound_code(client, google, monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:5173")
    query = _start_login(client, google)
    response = client.get("/auth/sso/google/callback", params={"code": "auth-code", "state": query["state"][0]}, follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("http://localhost:5173/sso/callback#code=")
    assert "access_token" not in location
    code = location.split("#code=", 1)[1]

    exchanged = client.post("/auth/sso/exchange", json={"code": code})
    assert exchanged.status_code == 200 and "access_token" in exchanged.json()
    assert client.post("/auth/sso/exchange", json={"code": code}).status_code == 400  # single use

    # A code planted in another browser (no binding cookie) does not work.
    planted, _binding = sso_service.create_login_handoff({"access_token": "x"})
    client.cookies.clear()
    assert client.post("/auth/sso/exchange", json={"code": planted}).status_code == 400


def test_sso_errors_redirect_with_a_code_not_details(client, monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:5173")
    response = client.get("/auth/sso/google/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:5173/sso/callback#error=provider_denied"


def test_linking_starts_with_an_authenticated_post(client, google, make_user, login):
    headers = bearer(login(make_user()))
    assert client.get("/auth/sso/google/link", headers=headers).status_code == 405
    response = client.post("/auth/sso/google/link", headers=headers)
    assert response.status_code == 200
    assert response.json()["authorization_url"].startswith(GOOGLE.authorize_url)
    assert "genesis_sso_state" in response.headers["set-cookie"]
    assert client.post("/auth/sso/google/link").status_code == 401


def test_completed_link_hands_the_web_app_a_session(client, google, make_user, login, db, monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:5173")
    user = make_user()
    start = client.post("/auth/sso/google/link", headers=bearer(login(user)))
    query = parse_qs(urlsplit(start.json()["authorization_url"]).query)
    google["nonce"] = query["nonce"][0]
    response = client.get("/auth/sso/google/callback", params={"code": "auth-code", "state": query["state"][0]}, follow_redirects=False)
    assert response.status_code == 302
    fragment = response.headers["location"].split("#", 1)[1]
    params = parse_qs(fragment)
    assert params["linked"] == ["google"]
    tokens = client.post("/auth/sso/exchange", json={"code": params["code"][0]}).json()
    assert decode_token(tokens["access_token"])["sub"] == str(user.id)
    assert db.query(OAuthAccount).filter(OAuthAccount.user_id == str(user.id), OAuthAccount.provider == "google").count() == 1
