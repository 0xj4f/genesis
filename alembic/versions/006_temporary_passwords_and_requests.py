"""Temporary passwords and the account request queue.

Revision ID: 006
Revises: 005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("password_expires_at", sa.DateTime(), nullable=True))

    op.create_table(
        "account_requests",
        sa.Column("id", mysql.CHAR(36), primary_key=True),
        sa.Column("user_id", mysql.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("requester_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_requested_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", mysql.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_account_requests_user_status", "account_requests", ["user_id", "status"])
    op.create_index("ix_account_requests_status_last", "account_requests", ["status", "last_requested_at"])


def downgrade():
    # Dropping the table drops its indexes; dropping the FK-backing index first fails on MySQL.
    op.drop_table("account_requests")
    op.drop_column("users", "password_expires_at")
    op.drop_column("users", "must_change_password")
