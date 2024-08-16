# models.py
# from sqlalchemy import Column, String, Boolean, UUID, ForeignKey
# from sqlalchemy.orm import relationship
# from .database import Base
#
#
# class User(Base):
#     __tablename__ = "users"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
#     username = Column(String, unique=True, index=True)
#     email = Column(String, unique=True, index=True)
#     hashed_password = Column(String)
#     is_active = Column(Boolean, default=True)
#     is_superuser = Column(Boolean, default=False)
#
#     profile = relationship("Profile", back_populates="user")
#
#
# class Profile(Base):
#     __tablename__ = "profiles"
#
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
#     first_name = Column(String, index=True)
#     last_name = Column(String, index=True)
#     phone_number = Column(String, index=True)
#     address = Column(String, index=True)
#     city = Column(String, index=True)
#     state = Column(String, index=True)
#     postal_code = Column(String, index=True)
#     country = Column(String, index=True)
#
#     user = relationship("User", back_populates="profile")

from sqlalchemy import Column, String, Boolean, ForeignKey, create_engine
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
import uuid

Base = declarative_base()


# SQLAlchemy User Model
class User(Base):
    __tablename__ = "users"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    username = Column(String(150), unique=True, index=True)
    email = Column(String(254), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(100), nullable=True)

    profile = relationship("Profile", back_populates="user", uselist=False)


# SQLAlchemy Profile Model
class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(CHAR(36), ForeignKey("users.id"), primary_key=True)
    first_name = Column(String(30), index=True)
    last_name = Column(String(30), index=True)
    phone_number = Column(String(20), index=True)
    address = Column(String(255), index=True)
    city = Column(String(100), index=True)
    state = Column(String(100), index=True)
    postal_code = Column(String(20), index=True)
    country = Column(String(56), index=True)

    user = relationship("User", back_populates="profile")
