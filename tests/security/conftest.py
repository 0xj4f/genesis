"""Isolated security tests; no running application or production database needed."""

import os
import secrets
from uuid import uuid4

# Without RSA key files (e.g. in CI) the app needs an explicit development
# signing secret; there is no committed default any more. Must run before
# app.config is imported. A local .env with RSA keys still takes precedence.
os.environ.setdefault("OAUTH_SECRET_KEY", secrets.token_urlsafe(48))

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.session import Base, get_db
from app.models.user_db_model import User
from app.middleware import security
from app.utils.security_store import MemorySecurityStore


@pytest.fixture
def clock():
    return [1000.0]


@pytest.fixture
def store(clock, monkeypatch):
    store = MemorySecurityStore(clock=lambda: clock[0])
    monkeypatch.setattr(security, "get_security_store", lambda: store)
    return store


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'security.db'}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture
def db(sessions):
    with sessions() as session:
        yield session


@pytest.fixture
def client(sessions, store):
    def override_db():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db):
    def create(role="user", **kwargs):
        suffix = uuid4().hex[:12]
        user = User(
            username=f"user_{suffix}", email=f"{suffix}@example.com", role=role,
            password=bcrypt.hashpw(b"ValidPassword123!", bcrypt.gensalt(rounds=4)).decode(),
            **kwargs,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return create


@pytest.fixture
def login(client):
    def authenticate(user):
        response = client.post("/token", data={"username": user.username, "password": "ValidPassword123!"})
        assert response.status_code == 200, response.text
        return response.json()
    return authenticate
