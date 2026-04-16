from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from uuid import uuid4
from app.database.session import Base


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    client_secret_hash = Column(String(255), nullable=False)
    client_name = Column(String(100), unique=True, nullable=False)
    redirect_uris = Column(JSON, nullable=False)
    allowed_scopes = Column(JSON, nullable=False)
    allowed_audiences = Column(JSON, nullable=False)
    grant_types = Column(JSON, nullable=False, default=lambda: ["authorization_code", "client_credentials"])
    is_active = Column(Boolean, nullable=False, default=True)
    is_confidential = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<OAuthClient(id={self.id}, name={self.client_name})>"
