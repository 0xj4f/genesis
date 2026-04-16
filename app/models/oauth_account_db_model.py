from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, UniqueConstraint, JSON
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from uuid import uuid4
from sqlalchemy.orm import relationship
from app.database.session import Base


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    provider = Column(String(20), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=True)
    provider_username = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    raw_userinfo = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        Index("ix_oauth_accounts_user_provider", "user_id", "provider"),
    )

    def __repr__(self):
        return f"<OAuthAccount(provider={self.provider}, user_id={self.user_id})>"
