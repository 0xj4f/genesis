"""initial schema with iam tables

Revision ID: 001
Revises:
Create Date: 2026-04-16 13:42:04.518785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR, JSON


revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- users table (create if not exists, then add IAM columns) ----
    op.create_table(
        "users",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password", sa.Text, nullable=True),
        sa.Column("disabled", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_modified", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("email_verified_at", sa.DateTime, nullable=True),
        sa.Column("auth_provider", sa.String(20), nullable=False, server_default="native"),
        sa.Column("auth_provider_id", sa.String(255), nullable=True),
        sa.Column("is_native", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("last_login_method", sa.String(20), nullable=True),
        if_not_exists=True,
    )

    # ---- profiles table ----
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("given_name", sa.String(100), nullable=False),
        sa.Column("family_name", sa.String(100), nullable=False),
        sa.Column("nick_name", sa.String(100), nullable=True),
        sa.Column("picture", sa.String(255), nullable=True),
        sa.Column("picture_key", sa.String(255), nullable=True),
        sa.Column("picture_updated_at", sa.DateTime, nullable=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("sub", sa.String(255), nullable=False),
        sa.Column("locale", sa.String(10), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # ---- oauth_accounts table ----
    op.create_table(
        "oauth_accounts",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("user_id", CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("provider_username", sa.String(255), nullable=True),
        sa.Column("access_token", sa.Text, nullable=True),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("token_expires_at", sa.DateTime, nullable=True),
        sa.Column("raw_userinfo", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )
    op.create_index("ix_oauth_accounts_user_provider", "oauth_accounts", ["user_id", "provider"])

    # ---- sessions table ----
    op.create_table(
        "sessions",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("user_id", CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("refresh_token_jti", CHAR(36), unique=True, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("login_method", sa.String(20), nullable=False, server_default="password"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_activity_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("revoked_reason", sa.String(100), nullable=True),
    )
    op.create_index("ix_sessions_user_active", "sessions", ["user_id", "is_active"])
    op.create_index("ix_sessions_refresh_jti", "sessions", ["refresh_token_jti"])

    # ---- oauth_clients table ----
    op.create_table(
        "oauth_clients",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("client_name", sa.String(100), unique=True, nullable=False),
        sa.Column("redirect_uris", JSON, nullable=False),
        sa.Column("allowed_scopes", JSON, nullable=False),
        sa.Column("allowed_audiences", JSON, nullable=False),
        sa.Column("grant_types", JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("is_confidential", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ---- authorization_codes table ----
    op.create_table(
        "authorization_codes",
        sa.Column("code", CHAR(64), primary_key=True),
        sa.Column("client_id", CHAR(36), sa.ForeignKey("oauth_clients.id"), nullable=False),
        sa.Column("user_id", CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("redirect_uri", sa.String(2048), nullable=False),
        sa.Column("scope", sa.String(500), nullable=False),
        sa.Column("nonce", sa.String(255), nullable=True),
        sa.Column("code_challenge", sa.String(128), nullable=True),
        sa.Column("code_challenge_method", sa.String(10), nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ---- jwk_keys table ----
    op.create_table(
        "jwk_keys",
        sa.Column("kid", sa.String(64), primary_key=True),
        sa.Column("algorithm", sa.String(10), nullable=False, server_default="RS256"),
        sa.Column("public_key_pem", sa.Text, nullable=False),
        sa.Column("private_key_pem", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("rotated_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("authorization_codes")
    op.drop_table("jwk_keys")
    op.drop_table("oauth_clients")
    op.drop_index("ix_sessions_refresh_jti", "sessions")
    op.drop_index("ix_sessions_user_active", "sessions")
    op.drop_table("sessions")
    op.drop_index("ix_oauth_accounts_user_provider", "oauth_accounts")
    op.drop_table("oauth_accounts")
    op.drop_table("profiles")
    op.drop_table("users")
