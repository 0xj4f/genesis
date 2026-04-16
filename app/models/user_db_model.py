from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.types import String as SqlString
from sqlalchemy.sql import func
from uuid import uuid4
from sqlalchemy.orm import relationship
from app.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(SqlString(100), unique=True, nullable=False)
    email = Column(SqlString(255), unique=True, nullable=False)
    password = Column(Text, nullable=True)  # Nullable: SSO-only users have no password
    disabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())
    last_modified = Column(DateTime, onupdate=func.now(), default=func.now())

    # IAM fields
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    auth_provider = Column(String(20), nullable=False, default="native")  # native, google, github, facebook
    auth_provider_id = Column(String(255), nullable=True)
    is_native = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    last_login_method = Column(String(20), nullable=True)  # password, google, github, facebook
    role = Column(String(20), nullable=False, default="user")  # user, admin, root

    # Relationships
    profile = relationship("Profile", uselist=False, back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
