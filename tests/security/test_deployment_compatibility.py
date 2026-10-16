"""Regression checks for migration startup and existing seeded ROOT responses."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.models.profile_api_model import ProfileCreate
from app.models.user_api_model import UserCreate, UserUpdate


@pytest.mark.parametrize("password", ["a" * 64, "database@password%with spaces!:/#"])
def test_alembic_accepts_encoded_database_passwords(password):
    # Render the pre-004 migrations offline so this exercises the real Alembic
    # configuration without requiring a database or printing connection URLs.
    env = {**os.environ, "MYSQL_DEV_PASSWORD": password, "ENVIRONMENT": "development"}
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "003", "--sql"],
                            cwd=Path(__file__).resolve().parents[2], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_existing_root_user_and_profile_serialize_internal_email(client, make_user, login, db):
    from app.models.profile_db_model import Profile
    user = make_user(role="root")
    user.email = "adam@genesis.local"
    db.add(Profile(user_id=user.id, given_name="Adam", family_name="Root", email=user.email, sub=user.id))
    db.commit()
    tokens = login(user)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    for path in ("/users/me/", "/profile/me/"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["email"] == "adam@genesis.local"


def test_request_email_validation_is_still_enforced():
    for model, payload in [
        (UserCreate, {"username": "test", "email": "adam@genesis.local", "password": "ValidPassword123!"}),
        (UserUpdate, {"email": "adam@genesis.local"}),
        (ProfileCreate, {"given_name": "Test", "family_name": "User", "sub": "test", "email": "not-an-email"}),
    ]:
        with pytest.raises(ValidationError):
            model(**payload)
