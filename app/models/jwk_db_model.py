from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database.session import Base


class JWKKey(Base):
    __tablename__ = "jwk_keys"

    kid = Column(String(64), primary_key=True)
    algorithm = Column(String(10), nullable=False, default="RS256")
    public_key_pem = Column(Text, nullable=False)
    private_key_pem = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_current = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())
    rotated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<JWKKey(kid={self.kid}, is_current={self.is_current}, is_active={self.is_active})>"
