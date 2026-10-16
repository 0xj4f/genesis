import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from app.auth.auth import create_access_token, create_refresh_token, decode_token
from app.config import Settings
from app.database.session_db_interface import update_session_jti_db
from app.middleware.security import SecurityMiddleware
from app.models.oauth_client_api_model import OAuthClientCreate
from app.models.profile_api_model import ProfileUpdate
from app.models.profile_db_model import Profile
from app.models.session_db_model import Session as LoginSession
from app.models.user_api_model import UserCreate
from app.models.user_db_model import User as UserModel
from app.services import sso_service
from app.services.picture_service import _resize_and_convert, MAX_FILE_SIZE
from app.services.storage_service import LocalStorageBackend
from app.utils.security import verify_password
from app.utils.security_store import MemorySecurityStore, SecurityStoreUnavailable


def bearer(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_global_limit_is_sliding_per_ip_and_ignores_forwarding_headers(client, clock):
    for i in range(30):
        response = client.get("/health", headers={"X-Forwarded-For": f"192.0.2.{i}", "X-Real-IP": f"192.0.2.{i}"})
        assert response.status_code == 200
    denied = client.get("/health")
    assert denied.status_code == 429
    assert denied.headers["retry-after"] == "1"
    assert denied.headers["cache-control"] == "no-store"
    clock[0] += 1.001
    assert client.get("/health").status_code == 200


def test_credential_limits_shared_between_login_registration_and_oauth(client, clock):
    paths = ["/token", "/admin/login", "/users/", "/oauth/token"]
    for i in range(10):
        assert client.post(paths[i % 4]).status_code == 422
    denied = client.post("/token")
    assert denied.status_code == 429
    assert denied.headers["retry-after"] == "60"
    assert client.get("/health").status_code == 200
    clock[0] += 60
    assert client.post("/token").status_code == 422


def test_rate_store_is_atomic_and_bounded():
    store = MemorySecurityStore(max_keys=1, clock=lambda: 1)
    with ThreadPoolExecutor(max_workers=16) as pool:
        outcomes = list(pool.map(lambda _: store.check_rate("same-ip", 30, 1), range(100)))
    assert outcomes.count(0) == 30
    with pytest.raises(SecurityStoreUnavailable):
        store.check_rate("other-ip", 30, 1)


def test_request_limits_reject_declared_and_chunked_bodies_before_parsing(client):
    assert client.post("/users/", content=b"{}", headers={"Content-Length": "6291457"}).status_code == 413
    assert client.post("/users/", content=iter([b"x" * (3 * 1024 * 1024)] * 3)).status_code == 413


def test_actual_chunked_limit_without_content_length(store):
    called = []

    async def downstream(scope, receive, send):
        called.append(True)

    messages = iter([
        {"type": "http.request", "body": b"x" * 800, "more_body": True},
        {"type": "http.request", "body": b"x" * 800, "more_body": False},
    ])
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    middleware = SecurityMiddleware(downstream, Settings(MAX_REQUEST_BODY_BYTES=1024))
    asyncio.run(middleware({"type": "http", "method": "POST", "path": "/upload", "headers": [], "client": ("192.0.2.1", 1)}, receive, send))
    assert sent[0]["status"] == 413
    assert not called


def test_security_store_capacity_failure_fails_closed(client, store, monkeypatch):
    def unavailable(*args):
        raise SecurityStoreUnavailable()
    monkeypatch.setattr(store, "check_rate", unavailable)
    assert client.get("/health").status_code == 503


def test_secure_headers_and_cors_on_rejections(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    for _ in range(29):
        client.get("/health")
    limited = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert limited.status_code == 429
    assert limited.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.parametrize("method,path", [("get", "/users/"), ("get", "/users/" + str(uuid4())), ("put", "/users/" + str(uuid4())), ("delete", "/users/" + str(uuid4())), ("post", "/users/search")])
def test_user_data_requires_authentication(client, method, path):
    response = getattr(client, method)(path, **({"json": {}} if method in {"put", "post"} else {}))
    assert response.status_code == 401


def test_users_cannot_read_change_or_delete_other_accounts(client, make_user, login, db):
    owner, other = make_user(), make_user()
    headers = bearer(login(owner))
    path = f"/users/{other.id}"
    assert client.get(path, headers=headers).status_code == 403
    assert client.put(path, headers=headers, json={"password": "ChangedPassword123!"}).status_code == 403
    assert client.delete(path, headers=headers).status_code == 403
    assert client.get("/users/", headers=headers).status_code == 403
    assert client.post("/users/search", headers=headers, json={"email": other.email}).status_code == 403
    assert client.get(f"/users/{owner.id}", headers=headers).status_code == 200
    assert client.put(f"/users/{owner.id}", headers=headers, json={"username": owner.username}).status_code == 200


def test_admin_cannot_demote_root_or_change_root_password(client, make_user, login):
    admin, root = make_user(role="admin"), make_user(role="root")
    headers = bearer(login(admin))
    assert client.post(f"/admin/users/{root.id}/role", headers=headers, json={"role": "user"}).status_code == 403
    assert client.put(f"/users/{root.id}", headers=headers, json={"password": "ChangedPassword123!"}).status_code == 403
    assert client.delete(f"/users/{root.id}", headers=headers).status_code == 403


def test_registration_profile_and_owner_updates_still_work(client, login, db):
    data = {"username": "normal_user", "email": "normal@example.com", "password": "ValidPassword123!"}
    registered = client.post("/users/", json=data)
    assert registered.status_code == 200, registered.text
    assert "password" not in registered.json()
    tokens = login(SimpleNamespace(username=data["username"]))
    headers = bearer(tokens)
    profile = client.post("/profile/", headers=headers, json={"given_name": "Normal", "family_name": "User", "sub": registered.json()["id"]})
    assert profile.status_code == 200, profile.text
    assert client.put("/profile/me/", headers=headers, json={"city": "Manila"}).json()["city"] == "Manila"
    assert client.delete(f"/users/{registered.json()['id']}", headers=headers).status_code == 200
    assert client.get("/users/me/", headers=headers).status_code == 401


def test_session_revocation_invalidates_access_and_refresh(client, make_user, login):
    tokens = login(make_user())
    sid = decode_token(tokens["access_token"])["sid"]
    headers = bearer(tokens)
    assert client.delete(f"/auth/sessions/{sid}", headers=headers).status_code == 200
    assert client.get("/users/me/", headers=headers).status_code == 401
    assert client.post("/token/validate", headers=headers).status_code == 401
    assert client.get("/oauth/userinfo", headers=headers).status_code == 401
    assert client.post("/refresh_token", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).status_code == 401


def test_refresh_rotation_preserves_valid_flow_and_detects_replay(client, make_user, login):
    tokens = login(make_user())
    old = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    rotated = client.post("/refresh_token", headers=old)
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]
    assert client.get("/users/me/", headers=bearer(rotated.json())).status_code == 200
    replay = client.post("/refresh_token", headers=old)
    assert replay.status_code == 401
    assert "rotated" in replay.json()["detail"]
    assert client.get("/users/me/", headers=bearer(rotated.json())).status_code == 401


def test_expired_mismatched_and_unbound_refresh_tokens_rejected(client, make_user, login, db):
    user, other = make_user(), make_user()
    tokens = login(user)
    payload = decode_token(tokens["refresh_token"], expected_type="refresh")
    row = db.get(LoginSession, payload["sid"])
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.post("/refresh_token", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).status_code == 401
    row.expires_at = datetime.utcnow() + timedelta(days=1)
    db.commit()
    for claims in [{"sub": user.id}, {"sub": other.id, "sid": row.id, "jti_override": row.refresh_token_jti}]:
        token, _ = create_refresh_token(claims)
        assert client.post("/refresh_token", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    db.refresh(row)
    assert row.is_active


@pytest.mark.parametrize("username,password", [("", "ValidPassword123!"), (" " * 5, "ValidPassword123!"), ("x" * 101, "ValidPassword123!"), ("bad\nname", "ValidPassword123!"), ("valid", "Aa1!" + "x" * 69), ("valid", "Aa1!" + "界" * 23)])
def test_invalid_user_input_rejected(username, password):
    with pytest.raises(ValidationError):
        UserCreate(username=username, email="test@example.com", password=password)


def test_long_login_password_is_rejected_without_hash_error(client, make_user):
    response = client.post("/token", data={"username": make_user().username, "password": "a" * 73})
    assert response.status_code == 401
    assert not verify_password("a" * 73, "invalid hash")


@pytest.mark.parametrize("value", [{"mobile_number": "1" * 21}, {"city": "x" * 101}, {"picture": "javascript:alert(1)"}, {"picture": "//evil.example/image"}, {"date_of_birth": "2999-01-01"}])
def test_invalid_profile_fields_rejected(value):
    with pytest.raises(ValidationError):
        ProfileUpdate(**value)


@pytest.mark.parametrize("uri", ["javascript:alert(1)", "https://app.example/callback#fragment", "https://user:pass@app.example/callback", "http://app.example/callback", "//app.example/callback"])
def test_unsafe_oauth_redirects_rejected(uri):
    with pytest.raises(ValidationError):
        OAuthClientCreate(client_name="test", redirect_uris=[uri], allowed_scopes=["openid"], allowed_audiences=["genesis-api"])


@pytest.mark.parametrize("header", ["Basic !!!", "Basic /w==", "Basic YWJj"])
def test_malformed_basic_auth_is_401(client, header):
    assert client.post("/oauth/token", headers={"Authorization": header}, data={"grant_type": "client_credentials"}).status_code == 401


def test_invalid_and_oversized_uploads_are_client_errors(client, make_user, login):
    headers = bearer(login(make_user()))
    for data, content_type in [(b"\x89PNGbroken", "image/png"), (b"RIFFnot-webp", "image/webp"), (b"<svg></svg>", "image/svg+xml"), (b"x" * (MAX_FILE_SIZE + 1), "image/png")]:
        response = client.post("/profile/me/picture", headers=headers, files={"picture": ("avatar.png", data, content_type)})
        assert response.status_code == 400, response.text


def test_valid_image_converts_and_oversized_dimensions_reject(monkeypatch):
    source = io.BytesIO()
    Image.new("RGB", (800, 600)).save(source, "PNG")
    processed = _resize_and_convert(source.getvalue())
    with Image.open(io.BytesIO(processed)) as image:
        assert image.format == "WEBP"
        assert image.size == (400, 300)
    monkeypatch.setattr("app.services.picture_service.MAX_IMAGE_PIXELS", 100)
    with pytest.raises(HTTPException) as error:
        _resize_and_convert(source.getvalue())
    assert error.value.status_code == 400


def test_upload_missing_profile_does_not_write_file(client, make_user, login, monkeypatch):
    def unexpected_storage():
        raise AssertionError("Storage must not be used for missing profile")
    monkeypatch.setattr("app.services.picture_service.get_storage_backend", unexpected_storage)
    source = io.BytesIO()
    Image.new("RGB", (10, 10)).save(source, "PNG")
    response = client.post("/profile/me/picture", headers=bearer(login(make_user())), files={"picture": ("test.png", source.getvalue(), "image/png")})
    assert response.status_code == 404


def test_local_storage_rejects_path_traversal(tmp_path):
    storage = LocalStorageBackend(str(tmp_path / "uploads"), "https://auth.example")
    for key in ["../secret", "/tmp/secret", "."]:
        with pytest.raises(ValueError):
            asyncio.run(storage.delete(key))


def test_unverified_provider_email_cannot_link_verified_existing_user(db, make_user, monkeypatch):
    existing = make_user(email_verified=True)
    provider = SimpleNamespace(name="google")
    monkeypatch.setattr(sso_service, "_create_oauth_account", lambda *a: pytest.fail("Must not link unverified email"))
    with pytest.raises(HTTPException) as error:
        sso_service._handle_login_or_register(db, provider, {"provider_user_id": "attacker", "email": existing.email, "email_verified": False}, "token", None, None, {}, None)
    assert error.value.status_code == 409


def test_provider_email_verified_requires_boolean_true():
    result = sso_service._normalize_userinfo(SimpleNamespace(name="github", field_map={}), {"sub": "123", "email_verified": "false"})
    assert result["email_verified"] is False


def test_sso_state_expires_is_single_use_and_binds_to_browser(client, monkeypatch, clock, store):
    provider = SimpleNamespace(name="google", client_id="client", redirect_uri="https://auth.example/auth/sso/google/callback", scopes=["openid", "email"], authorize_url="https://provider.example/authorize")
    monkeypatch.setattr(sso_service, "get_provider", lambda name: provider)
    monkeypatch.setattr(sso_service, "get_security_store", lambda: store)
    response = client.get("/auth/sso/google/authorize", follow_redirects=False)
    assert response.status_code == 302
    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert parse_qs(urlsplit(response.headers["location"]).query)["scope"] == ["openid email"]
    client.cookies.clear()
    mismatch = client.get("/auth/sso/google/callback", params={"code": "unused", "state": state})
    assert mismatch.status_code == 400
    assert "browser" in mismatch.json()["detail"]
    assert sso_service.validate_state(state)["provider"] == "google"
    with pytest.raises(HTTPException):
        sso_service.validate_state(state)
    _, expired = sso_service.generate_authorize_url("google")
    clock[0] += 601
    with pytest.raises(HTTPException):
        sso_service.validate_state(expired)


def test_production_settings_require_https_and_hosts_without_external_state_service():
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production")
    valid = dict(ENVIRONMENT="production", OAUTH_PRIVATE_KEY_PATH="private.pem", OAUTH_PUBLIC_KEY_PATH="public.pem", OAUTH_ISSUER="https://auth.example", CORS_ALLOW_ORIGINS="https://app.example", ALLOWED_HOSTS="auth.example")
    assert Settings(**valid).allowed_hosts == ["auth.example"]
    for key, value in [("OAUTH_ISSUER", "http://auth.example"), ("CORS_ALLOW_ORIGINS", "*"), ("ALLOWED_HOSTS", "*"), ("OAUTH_ALGORITHM", "HS256")]:
        with pytest.raises(ValidationError):
            Settings(**{**valid, key: value})


@pytest.mark.parametrize("token", ["invalid", "a.b.c", "", "eyJhbGciOiJub25lIn0.e30."])
def test_malformed_tokens_are_401(client, token):
    response = client.get("/users/me/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_rsa_verification_rejects_hmac_algorithm_confusion(monkeypatch):
    import base64
    import hashlib
    import hmac
    from cryptography.hazmat.primitives import serialization
    from app.auth import auth
    from app.auth.keys import generate_rsa_key_pair

    _, public_pem = generate_rsa_key_pair()
    public = serialization.load_pem_public_key(public_pem)
    der = public.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    monkeypatch.setattr(auth, "get_verification_key_by_kid", lambda kid: (public, "RS256"))
    # Construct the attack manually; PyJWT also rejects DER keys when encoding
    # HMAC tokens, but the server must reject an independently forged token.
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=")
    payload = base64.urlsafe_b64encode(b'{"sub":"attacker"}').rstrip(b"=")
    unsigned = header + b"." + payload
    signature = base64.urlsafe_b64encode(hmac.new(der, unsigned, hashlib.sha256).digest()).rstrip(b"=")
    forged = (unsigned + b"." + signature).decode()
    with pytest.raises(HTTPException) as error:
        decode_token(forged)
    assert error.value.status_code == 401


def test_production_key_lookup_never_falls_back_to_development_secret(monkeypatch):
    from app.auth import keys
    monkeypatch.setattr(keys, "settings", keys.settings.model_copy(update={"ENVIRONMENT": "production"}))
    monkeypatch.setattr(keys, "_load_keys", lambda: {})
    with pytest.raises(RuntimeError):
        keys.get_signing_key()
    assert keys.get_verification_key_by_kid("") is None


def test_sso_non_ascii_state_is_client_error(client):
    client.cookies.set("genesis_sso_state", "valid-ascii")
    result = client.get("/auth/sso/google/callback", params={"state": "界", "code": "unused"})
    assert result.status_code == 400


def test_duplicate_registration_commit_rolls_back(db):
    from app.database.user_db_interface import create_user_db
    data = UserCreate(username="duplicate", email="duplicate@example.com", password="ValidPassword123!")
    # The database interface receives hashes from the service; two concurrent
    # service prechecks can both succeed, so the final commit must also guard it.
    data.password = "already-hashed"
    create_user_db(db, data)
    with pytest.raises(HTTPException) as error:
        create_user_db(db, data)
    assert error.value.status_code == 400
    assert db.query(UserModel).count() == 1


def test_provider_verified_email_can_still_link_existing_user(db, make_user, monkeypatch):
    existing = make_user(email_verified=False)
    linked = []
    monkeypatch.setattr(sso_service, "_create_oauth_account", lambda *args: linked.append(args))
    monkeypatch.setattr(sso_service, "_issue_tokens", lambda *args: {"access_token": "test"})
    result = sso_service._handle_login_or_register(db, SimpleNamespace(name="google"), {"provider_user_id": "verified-id", "email": existing.email, "email_verified": True}, "token", None, None, {}, None)
    assert result == {"access_token": "test"}
    assert len(linked) == 1
    db.refresh(existing)
    assert existing.email_verified is True


def test_email_change_does_not_inherit_verification(client, make_user, login, db):
    user = make_user(email_verified=True, email_verified_at=datetime.utcnow())
    tokens = login(user)
    response = client.put(f"/users/{user.id}", headers=bearer(tokens), json={"email": "new-unverified@example.com"})
    assert response.status_code == 200, response.text
    assert response.json()["email_verified"] is False
    refreshed = client.post("/refresh_token", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert refreshed.status_code == 200
    claims = decode_token(refreshed.json()["access_token"])
    assert claims["email"] == "new-unverified@example.com"
    assert claims["email_verified"] is False


def test_password_change_revokes_existing_sessions(client, make_user, login):
    user = make_user()
    first, second = login(user), login(user)
    response = client.put(f"/users/{user.id}", headers=bearer(first), json={"password": "ChangedPassword123!"})
    assert response.status_code == 200, response.text
    for tokens in (first, second):
        assert client.get("/users/me/", headers=bearer(tokens)).status_code == 401
        assert client.post("/refresh_token", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).status_code == 401
    assert client.post("/token", data={"username": user.username, "password": "ChangedPassword123!"}).status_code == 200
