from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.database.session import Base


class AuthorizationCode(Base):
    __tablename__ = "authorization_codes"

    code = Column(CHAR(64), primary_key=True)
    client_id = Column(CHAR(36), ForeignKey("oauth_clients.id"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    redirect_uri = Column(String(2048), nullable=False)
    scope = Column(String(500), nullable=False)
    nonce = Column(String(255), nullable=True)
    code_challenge = Column(String(128), nullable=True)
    code_challenge_method = Column(String(10), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<AuthorizationCode(code={self.code[:8]}..., client_id={self.client_id})>"
