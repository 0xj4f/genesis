from datetime import datetime
import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.database.session import Base


class UserRole(str, enum.Enum):
    root_admin = "root_admin"
    admin = "admin"
    user = "user"


class UserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    pending = "pending"


class AuthProvider(str, enum.Enum):
    native = "native"
    google = "google"
    facebook = "facebook"


class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.active)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    disabled_at = Column(DateTime, nullable=True)

    identities = relationship("UserIdentity", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("UserCredential", uselist=False, back_populates="user", cascade="all, delete-orphan")
    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_provider_subject"),)

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(Enum(AuthProvider), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    username = Column(String(100), nullable=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="identities")
    sessions = relationship("Session", back_populates="identity")


class UserCredential(Base):
    __tablename__ = "user_credentials"

    user_id = Column(CHAR(36), ForeignKey("users.id"), primary_key=True)
    password_hash = Column(Text, nullable=False)
    password_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    must_reset_password = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="credentials")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    identity_id = Column(CHAR(36), ForeignKey("user_identities.id"), nullable=False, index=True)
    refresh_token_hash = Column(Text, nullable=False)
    jti = Column(CHAR(36), nullable=False, unique=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True, index=True)
    revoked_reason = Column(String(128), nullable=True)

    user = relationship("User", back_populates="sessions")
    identity = relationship("UserIdentity", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
