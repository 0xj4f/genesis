"""update profile schema for ecommerce

Revision ID: 003
Revises: 002
Create Date: 2026-04-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ecommerce fields
    op.add_column("profiles", sa.Column("date_of_birth", sa.Date, nullable=True))
    op.add_column("profiles", sa.Column("mobile_number", sa.String(20), nullable=True))
    op.add_column("profiles", sa.Column("phone_verified", sa.Boolean, nullable=False, server_default=sa.text("0")))
    op.add_column("profiles", sa.Column("address_line1", sa.String(255), nullable=True))
    op.add_column("profiles", sa.Column("address_line2", sa.String(255), nullable=True))
    op.add_column("profiles", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("profiles", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("profiles", sa.Column("zip_code", sa.String(20), nullable=True))
    op.add_column("profiles", sa.Column("country", sa.String(100), nullable=True))

    # Remove deprecated fields
    op.drop_column("profiles", "locale")
    op.drop_column("profiles", "timezone")


def downgrade() -> None:
    op.add_column("profiles", sa.Column("locale", sa.String(10), nullable=True))
    op.add_column("profiles", sa.Column("timezone", sa.String(50), nullable=True))
    op.drop_column("profiles", "country")
    op.drop_column("profiles", "zip_code")
    op.drop_column("profiles", "state")
    op.drop_column("profiles", "city")
    op.drop_column("profiles", "address_line2")
    op.drop_column("profiles", "address_line1")
    op.drop_column("profiles", "phone_verified")
    op.drop_column("profiles", "mobile_number")
    op.drop_column("profiles", "date_of_birth")
