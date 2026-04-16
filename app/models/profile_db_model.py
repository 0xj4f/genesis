from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    given_name = Column(String(100), nullable=False)
    family_name = Column(String(100), nullable=False)
    nick_name = Column(String(100), nullable=True)
    picture = Column(String(255), nullable=True)  # Public URL
    picture_key = Column(String(255), nullable=True)  # Storage key for uploaded file
    picture_updated_at = Column(DateTime, nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    sub = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=True)  # e.g. "en-US"
    timezone = Column(String(50), nullable=True)  # e.g. "America/New_York"
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id}, email={self.email})>"
