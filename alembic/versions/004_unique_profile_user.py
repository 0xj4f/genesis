"""Enforce existing profile and provider-link uniqueness under concurrency.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    duplicates = op.get_bind().execute(sa.text(
        "SELECT user_id FROM profiles GROUP BY user_id HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates:
        raise RuntimeError("Duplicate profiles exist. Resolve duplicate profiles.user_id values before migration 004.")
    duplicate_links = op.get_bind().execute(sa.text(
        "SELECT user_id, provider FROM oauth_accounts GROUP BY user_id, provider HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicate_links:
        raise RuntimeError("Duplicate provider links exist. Resolve duplicate oauth_accounts (user_id, provider) values before migration 004.")
    op.create_unique_constraint("uq_profiles_user_id", "profiles", ["user_id"])
    op.create_unique_constraint("uq_user_provider", "oauth_accounts", ["user_id", "provider"])


def downgrade():
    # MySQL may remove the implicit FK index when the unique index replaces it.
    indexes = sa.inspect(op.get_bind()).get_indexes("profiles")
    if not any(not index["unique"] and index["column_names"][0] == "user_id" for index in indexes):
        op.create_index("ix_profiles_user_id", "profiles", ["user_id"])
    op.drop_constraint("uq_user_provider", "oauth_accounts", type_="unique")
    op.drop_constraint("uq_profiles_user_id", "profiles", type_="unique")
