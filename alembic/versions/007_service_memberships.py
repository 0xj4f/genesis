"""Services, per-service memberships and the registration source of each account.

With LEGACY_SERVICE_ID set (e.g. "shop"), every existing account came from that
service before services existed: it gets an ACTIVE membership there
(joined_via=backfill), former global admins become admins of that service only, and
active sessions are bound to it so signed-in users stay signed in. Root stays global.
Pending memberships for the other services are added at startup (sync_services).

Revision ID: 007
Revises: 006
"""

from datetime import datetime
from uuid import uuid4

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from app.config import get_settings

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "services",
        sa.Column("client_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("password_policy", sa.String(16), nullable=False, server_default="strict"),
        sa.Column("auto_enroll", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "service_memberships",
        sa.Column("id", mysql.CHAR(36), primary_key=True),
        sa.Column("user_id", mysql.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", sa.String(64), sa.ForeignKey("services.client_id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="user"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("joined_via", sa.String(16), nullable=False, server_default="auto"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("suspended_at", sa.DateTime(), nullable=True),
        sa.Column("suspended_by", mysql.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("user_id", "service_id", name="uq_service_memberships_user_service"),
    )
    op.create_index("ix_service_memberships_service_status", "service_memberships", ["service_id", "status"])

    op.add_column("users", sa.Column("registered_via", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("registration_ip", sa.String(45), nullable=True))
    op.add_column("users", sa.Column("registration_user_agent", sa.String(255), nullable=True))
    op.create_index("ix_users_registered_via", "users", ["registered_via"])

    op.add_column("sessions", sa.Column("service_id", sa.String(64), nullable=True))
    op.create_foreign_key("fk_sessions_service_id", "sessions", "services", ["service_id"], ["client_id"])

    settings = get_settings()
    legacy = settings.LEGACY_SERVICE_ID
    if legacy and not context.is_offline_mode():
        _backfill(legacy, settings.service_by_id(legacy))


def _backfill(legacy: str, declared) -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    bind.execute(
        sa.text("INSERT INTO services (client_id, name, password_policy, auto_enroll, is_active, created_at, updated_at) "
                "VALUES (:id, :name, :policy, :auto, :active, :now, :now)"),
        {"id": legacy, "name": declared.name if declared else legacy,
         "policy": declared.password_policy if declared else "strict",
         "auto": declared.auto_enroll if declared else True, "active": True, "now": now},
    )
    users = bind.execute(sa.text("SELECT id, role FROM users WHERE role <> 'root'")).fetchall()
    for user_id, role in users:
        bind.execute(
            sa.text("INSERT INTO service_memberships (id, user_id, service_id, role, status, joined_via, created_at, activated_at) "
                    "VALUES (:id, :user_id, :service, :role, 'active', 'backfill', :now, :now)"),
            {"id": str(uuid4()), "user_id": user_id, "service": legacy,
             "role": "admin" if role == "admin" else "user", "now": now},
        )
    bind.execute(sa.text("UPDATE users SET registered_via = :service WHERE role <> 'root'"), {"service": legacy})
    # Admin rights now belong to the service: a former global admin is an admin of the legacy service only.
    bind.execute(sa.text("UPDATE users SET role = 'user' WHERE role = 'admin'"))
    bind.execute(sa.text("UPDATE sessions SET service_id = :service WHERE is_active = :active"),
                 {"service": legacy, "active": True})


def downgrade():
    bind = op.get_bind()
    if not context.is_offline_mode():
        # Give service admins their global admin role back before the memberships go.
        bind.execute(sa.text(
            "UPDATE users SET role = 'admin' WHERE role = 'user' AND id IN "
            "(SELECT user_id FROM service_memberships WHERE role = 'admin')"
        ))
    op.drop_constraint("fk_sessions_service_id", "sessions", type_="foreignkey")
    op.drop_column("sessions", "service_id")
    op.drop_index("ix_users_registered_via", table_name="users")
    op.drop_column("users", "registration_user_agent")
    op.drop_column("users", "registration_ip")
    op.drop_column("users", "registered_via")
    op.drop_table("service_memberships")
    op.drop_table("services")
