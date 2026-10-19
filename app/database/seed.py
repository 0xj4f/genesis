"""Seed the ROOT superadmin user (Adam) if no root user exists."""

import secrets
import sys

from app.database.session import SessionLocal
from app.models.user_db_model import User
from app.models.profile_db_model import Profile
from app.utils.security import hash_password
from app.config import get_settings
from app.models.user_api_model import validate_password_strength


def seed_adam():
    settings = get_settings()
    db = SessionLocal()
    try:
        existing_root = db.query(User).filter(User.role == "root").first()
        if existing_root:
            print(f"[seed] ROOT user already exists: {existing_root.username} ({existing_root.email})")
            return

        if settings.BOOTSTRAP_ROOT_PASSWORD:
            password = settings.BOOTSTRAP_ROOT_PASSWORD.get_secret_value()
            validate_password_strength(password)
        elif settings.ENVIRONMENT == "production":
            raise RuntimeError("Set BOOTSTRAP_ROOT_PASSWORD before creating the production ROOT user")
        else:
            password = secrets.token_urlsafe(16)
        hashed = hash_password(password)

        adam = User(
            username="adam",
            email="adam@genesis.local",
            password=hashed,
            is_active=True,
            email_verified=True,
            auth_provider="native",
            is_native=True,
            role="root",
        )
        db.add(adam)
        db.flush()

        profile = Profile(
            user_id=str(adam.id),
            given_name="Adam",
            family_name="Root",
            nick_name="0xadam",
            email="adam@genesis.local",
            sub=str(adam.id),
        )
        db.add(profile)
        db.commit()

        print("=" * 60)
        print("  GENESIS ROOT USER CREATED")
        print("=" * 60)
        print(f"  Username: adam")
        print(f"  Email:    adam@genesis.local")
        if settings.ENVIRONMENT != "production":
            print(f"  Password: {password}")
        else:
            print("  Password: supplied via BOOTSTRAP_ROOT_PASSWORD (not logged)")
        print(f"  Role:     root")
        print("=" * 60)
        print("  SAVE THIS PASSWORD. It will not be shown again.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"[seed] Error seeding Adam: {e}", file=sys.stderr)
        if settings.ENVIRONMENT == "production":
            raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_adam()
