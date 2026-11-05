from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from uuid import uuid4
from app.database.session import Base

PASSWORD_RESET = "password_reset"


class AccountRequest(Base):
    """A user's request for administrator help (e.g. a password reset), queued
    in the admin console until an administrator resolves or dismisses it."""

    __tablename__ = "account_requests"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False)  # "password_reset"
    status = Column(String(20), nullable=False, default="open")  # open, resolved, dismissed
    # Repeat requests while one is open bump this instead of adding rows.
    request_count = Column(Integer, nullable=False, default=1)
    requester_ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    last_requested_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("ix_account_requests_user_status", "user_id", "status"),
        Index("ix_account_requests_status_last", "status", "last_requested_at"),
    )
