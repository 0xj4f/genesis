"""Services (first-party applications) and each account's membership in them.

An account is shared by every service, but each service has its own membership:
- pending:   created automatically; the person has not signed in to that service yet.
- active:    the person registered or signed in there.
- suspended: an administrator of that service blocked them there (other services unaffected).
The role (user/admin) is also per service. Only the global "root" role spans all services.
"""

from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func

from app.database.session import Base

PENDING = "pending"
ACTIVE = "active"
SUSPENDED = "suspended"

# How a membership came to be.
JOINED_REGISTRATION = "registration"  # signed up on this service
JOINED_AUTO = "auto"                  # signed up elsewhere; waiting here as pending
JOINED_LOGIN = "login"                # first sign-in here activated it
JOINED_BACKFILL = "backfill"          # existing account when services were introduced
JOINED_ADMIN = "admin"                # created by an administrator of this service


class Service(Base):
    __tablename__ = "services"

    client_id = Column(String(64), primary_key=True)
    name = Column(String(100), nullable=False)
    password_policy = Column(String(16), nullable=False, default="strict")
    auto_enroll = Column(Boolean, nullable=False, default=True)
    # False once the deployment stops declaring it: sign-in there is refused.
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ServiceMembership(Base):
    __tablename__ = "service_memberships"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(String(64), ForeignKey("services.client_id"), nullable=False)
    role = Column(String(16), nullable=False, default="user")
    status = Column(String(16), nullable=False, default=PENDING)
    joined_via = Column(String(16), nullable=False, default=JOINED_AUTO)
    created_at = Column(DateTime, default=func.now())
    activated_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    suspended_at = Column(DateTime, nullable=True)
    suspended_by = Column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_service_memberships_user_service"),
        Index("ix_service_memberships_service_status", "service_id", "status"),
    )
