import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "smoke_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["OAUTH_SECRET_KEY"] = "smoke-test-secret"
    os.environ["ROOT_ADMIN_USERNAME"] = "root"
    os.environ["ROOT_ADMIN_EMAIL"] = "root@local"
    os.environ["ROOT_ADMIN_PASSWORD"] = "ChangeMeNow!123"

    import app.main as main_module

    importlib.reload(main_module)
    with TestClient(main_module.app) as test_client:
        yield test_client


def _register_and_login(client: TestClient, username: str, email: str, password: str) -> dict:
    reg_response = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert reg_response.status_code == 200, reg_response.text

    login_response = client.post(
        "/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    return login_response.json()


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_native_user_self_service_flow(client: TestClient):
    tokens = _register_and_login(client, "alice", "alice@example.com", "SecurePass!123")
    access_token = tokens["access_token"]

    me_response = client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "user"

    profile_update = client.put(
        "/profile/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "given_name": "Alice",
            "family_name": "Walker",
            "nick_name": "ali",
            "picture_url": "https://example.com/alice.png",
            "locale": "en-US",
        },
    )
    assert profile_update.status_code == 200, profile_update.text
    assert profile_update.json()["given_name"] == "Alice"


def test_refresh_rotation(client: TestClient):
    tokens = _register_and_login(client, "bob", "bob@example.com", "SecurePass!123")
    refresh_token = tokens["refresh_token"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200, refresh_response.text
    new_tokens = refresh_response.json()
    assert new_tokens["refresh_token"] != refresh_token


def test_root_admin_can_list_users(client: TestClient):
    login_response = client.post(
        "/auth/login",
        json={"username_or_email": "root", "password": "ChangeMeNow!123"},
    )
    assert login_response.status_code == 200, login_response.text
    access_token = login_response.json()["access_token"]

    users_response = client.get("/admin/users", headers={"Authorization": f"Bearer {access_token}"})
    assert users_response.status_code == 200, users_response.text
    assert isinstance(users_response.json(), list)
