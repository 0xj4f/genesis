from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class OAuthClientCreate(BaseModel):
    client_name: str
    redirect_uris: list[str]
    allowed_scopes: list[str]
    allowed_audiences: list[str]
    grant_types: list[str] = ["authorization_code", "client_credentials"]
    is_confidential: bool = True


class OAuthClientResponse(BaseModel):
    id: UUID
    client_name: str
    redirect_uris: list[str]
    allowed_scopes: list[str]
    allowed_audiences: list[str]
    grant_types: list[str]
    is_active: bool
    is_confidential: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OAuthClientWithSecret(OAuthClientResponse):
    client_secret: str  # Only returned on creation


class OAuthClientUpdate(BaseModel):
    client_name: Optional[str] = None
    redirect_uris: Optional[list[str]] = None
    allowed_scopes: Optional[list[str]] = None
    allowed_audiences: Optional[list[str]] = None
    grant_types: Optional[list[str]] = None
    is_active: Optional[bool] = None
