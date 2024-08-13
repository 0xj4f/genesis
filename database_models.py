from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String as SqlString
from sqlalchemy.sql import func
from uuid import uuid4
import sqlalchemy as sa

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(SqlString(100), unique=True, nullable=False)
    email = Column(SqlString(255), unique=True, nullable=False)
    password = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_modified = Column(DateTime, onupdate=func.now(), default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
