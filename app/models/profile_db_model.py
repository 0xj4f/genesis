from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Date, Boolean
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)

    # Identity
    given_name = Column(String(100), nullable=False)
    family_name = Column(String(100), nullable=False)
    nick_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    sub = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    mobile_number = Column(String(20), nullable=True)
    phone_verified = Column(Boolean, nullable=False, default=False)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Avatar
    picture = Column(String(255), nullable=True)
    picture_key = Column(String(255), nullable=True)
    picture_updated_at = Column(DateTime, nullable=True)

    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id}, email={self.email})>"
