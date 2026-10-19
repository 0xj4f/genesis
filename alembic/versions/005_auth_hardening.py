"""Auth hardening: email verification tokens, first-party OAuth clients, and no
stored SSO provider tokens.

Revision ID: 005
Revises: 004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", mysql.CHAR(36), primary_key=True),
        sa.Column("user_id", mysql.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", mysql.CHAR(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_email_verification_user", "email_verification_tokens", ["user_id", "purpose"])

    op.add_column(
        "oauth_clients",
        sa.Column("is_first_party", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Clients registered before consent existed were auto-approved; keep that.
    op.execute("UPDATE oauth_clients SET is_first_party = 1")

    # Provider access/refresh tokens and raw profiles were stored but never used.
    # Remove them so a database copy does not hand out third-party access.
    op.execute(
        "UPDATE oauth_accounts SET access_token = NULL, refresh_token = NULL, "
        "token_expires_at = NULL, raw_userinfo = NULL"
    )


def downgrade():
    # Cleared provider tokens cannot be restored (they were never used).
    op.drop_column("oauth_clients", "is_first_party")
    op.drop_index("ix_email_verification_user", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
