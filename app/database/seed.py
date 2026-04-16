"""Seed the ROOT superadmin user (Adam) if no root user exists."""

import secrets
import sys

from app.database.session import SessionLocal
from app.models.user_db_model import User
from app.models.profile_db_model import Profile
from app.utils.security import hash_password


def seed_adam():
    db = SessionLocal()
    try:
        existing_root = db.query(User).filter(User.role == "root").first()
        if existing_root:
            print(f"[seed] ROOT user already exists: {existing_root.username} ({existing_root.email})")
            return

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
        print(f"  Password: {password}")
        print(f"  Role:     root")
        print("=" * 60)
        print("  SAVE THIS PASSWORD. It will not be shown again.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"[seed] Error seeding Adam: {e}", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    seed_adam()
