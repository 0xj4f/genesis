from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from uuid import uuid4
from app.database.session import Base


class EmailVerificationToken(Base):
    """Single-use email verification link. Only a SHA-256 of the token is stored."""

    __tablename__ = "email_verification_tokens"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(CHAR(64), unique=True, nullable=False)
    email = Column(String(255), nullable=False)  # the address this link proves
    purpose = Column(String(20), nullable=False)  # "verify" or "change"
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("ix_email_verification_user", "user_id", "purpose"),
    )

    def __repr__(self):
        return f"<EmailVerificationToken(user_id={self.user_id}, purpose={self.purpose})>"
