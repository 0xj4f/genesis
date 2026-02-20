from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.database.session import Base


class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(CHAR(36), ForeignKey("users.id"), primary_key=True)
    given_name = Column(String(100), nullable=False)
    family_name = Column(String(100), nullable=False)
    nick_name = Column(String(100), nullable=True)
    picture_url = Column(String(512), nullable=True)
    locale = Column(String(32), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")
