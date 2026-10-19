"""Optional integration tests against a disposable MySQL database.

GENESIS_TEST_DATABASE_URL=mysql+pymysql://.../genesis_security
"""

import base64
import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.auth import create_refresh_token, decode_token
from app.database.authz_code_db_interface import mark_authz_code_used_db
from app.database.session import Base
from app.models.authz_code_db_model import AuthorizationCode
from app.models.oauth_client_db_model import OAuthClient
from app.models.session_db_model import Session as LoginSession
from app.models.user_db_model import User
from app.services import auth_service, oidc_service, sso_service
from app.models.oauth_account_db_model import OAuthAccount
from app.services.profile_service import create_profile_service
from app.services.session_service import create_session
from app.models.profile_api_model import ProfileCreate
from app.utils.security_store import MemorySecurityStore


@pytest.fixture
def mysql_sessions():
    url = os.getenv("GENESIS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set GENESIS_TEST_DATABASE_URL to an isolated MySQL database")
    engine = create_engine(url, pool_size=20, max_overflow=10)
    # These tests own the schema. Refuse a name that could be the real app DB.
    assert engine.url.database.endswith("_security"), "Use a disposable database ending in _security"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def mysql_user(mysql_sessions):
    with mysql_sessions() as db:
        user = User(username="concurrency", email="concurrency@example.com", password=None)
        db.add(user)
        db.commit()
        return user.id


def request():
    return SimpleNamespace(client=SimpleNamespace(host="192.0.2.1"), headers={})


def test_mysql_refresh_race_issues_only_one_token_pair(mysql_sessions, mysql_user, monkeypatch):
    jti = str(uuid4())
    with mysql_sessions() as db:
        sid = create_session(db, mysql_user, jti, request())
    token, _ = create_refresh_token({"sub": mysql_user, "sid": sid, "jti_override": jti})
    barrier = threading.Barrier(2)
    original_validate = auth_service.validate_refresh_against_session

    def both_validated(*args):
        result = original_validate(*args)
        barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(auth_service, "validate_refresh_against_session", both_validated)

    def refresh(_):
        with mysql_sessions() as db:
            try:
                return 200, auth_service.refresh_access_token_service(token, db, request())
            except HTTPException as error:
                return error.status_code, error.detail

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(refresh, range(2)))
    assert sorted(status for status, _ in results) == [200, 401]
    with mysql_sessions() as db:
        row = db.get(LoginSession, sid)
        assert row.refresh_token_jti != jti
        assert row.is_active is False  # Preserve replay revocation behavior.


def test_mysql_authorization_code_race_has_one_redemption(mysql_sessions, mysql_user, monkeypatch):
    verifier = "a" * 43
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    with mysql_sessions() as db:
        client = OAuthClient(client_name="race-client", client_secret_hash="unused", redirect_uris=["https://app.example/callback"], allowed_scopes=["openid"], allowed_audiences=["genesis-api"], grant_types=["authorization_code"], is_confidential=False)
        db.add(client)
        db.commit()
        client_id = client.id
        code = oidc_service.create_authorization_code(db, client_id, mysql_user, "https://app.example/callback", "openid", None, challenge, "S256")
    barrier = threading.Barrier(2)

    def consume_once(*args):
        barrier.wait(timeout=10)
        return mark_authz_code_used_db(*args)

    monkeypatch.setattr(oidc_service, "mark_authz_code_used_db", consume_once)

    def redeem(_):
        with mysql_sessions() as db:
            try:
                result = oidc_service.exchange_authorization_code(db, code, client_id, None, "https://app.example/callback", verifier, request())
                return 200, result
            except HTTPException as error:
                return error.status_code, error.detail

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(redeem, range(2)))
    assert sorted(status for status, _ in results) == [200, 400]
    with mysql_sessions() as db:
        assert db.get(AuthorizationCode, code).used
        assert db.query(LoginSession).count() == 1


def test_mysql_simultaneous_logins_respect_session_cap(mysql_sessions, mysql_user):
    barrier = threading.Barrier(12)

    def login(_):
        with mysql_sessions() as db:
            # Authentication starts a repeatable-read snapshot before the lock.
            assert db.get(User, mysql_user) is not None
            barrier.wait(timeout=10)
            return create_session(db, mysql_user, str(uuid4()), request())

    with ThreadPoolExecutor(max_workers=12) as pool:
        assert len(set(pool.map(login, range(12)))) == 12
    with mysql_sessions() as db:
        assert db.query(LoginSession).filter_by(is_active=True).count() == 5
        assert db.query(LoginSession).filter_by(revoked_reason="session_limit").count() == 7


def test_mysql_simultaneous_profile_creation_leaves_one_profile(mysql_sessions, mysql_user):
    barrier = threading.Barrier(2)

    def create(_):
        with mysql_sessions() as db:
            assert db.get(User, mysql_user) is not None
            barrier.wait(timeout=10)
            try:
                create_profile_service(db, SimpleNamespace(id=mysql_user, email="concurrency@example.com"), ProfileCreate(given_name="Race", family_name="Test"))
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create, range(2))) == [200, 400]


def test_mysql_concurrent_unlink_keeps_last_authentication_method(mysql_sessions, mysql_user):
    with mysql_sessions() as db:
        for provider in ["google", "github"]:
            db.add(OAuthAccount(user_id=mysql_user, provider=provider, provider_user_id=provider + "-123"))
        db.commit()
    barrier = threading.Barrier(2)

    def unlink(provider):
        with mysql_sessions() as db:
            assert db.get(User, mysql_user) is not None
            barrier.wait(timeout=10)
            try:
                sso_service.unlink_provider(db, mysql_user, provider)
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(unlink, ["google", "github"])) == [200, 400]
    with mysql_sessions() as db:
        assert db.query(OAuthAccount).count() == 1


def test_single_use_state_is_atomic_between_request_threads():
    store = MemorySecurityStore()
    state_key = str(uuid4())
    store.put_state(state_key, {"provider": "google"}, 60)
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: store.pop_state(state_key), range(100)))
    assert results.count({"provider": "google"}) == 1
    assert results.count(None) == 99
