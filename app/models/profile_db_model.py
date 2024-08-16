from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from uuid import uuid4

Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)  # You can change to UUID if preferred
    user_id = Column(CHAR(36), ForeignKey('users.id'), nullable=False)
    given_name = Column(String(100), nullable=False)
    family_name = Column(String(100), nullable=False)
    nick_name = Column(String(100), nullable=True)
    picture = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    email = Column(String(255), unique=True, nullable=False)
    sub = Column(String(255), nullable=False)

    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id}, email={self.email})>"
