from pydantic import BaseModel, Field, AfterValidator
from typing import Optional, Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID
from datetime import datetime


def validate_redirect(value: str) -> str:
    parsed = urlsplit(value)
    if (not parsed.netloc or parsed.fragment or parsed.username or parsed.password
            or any(c.isspace() or ord(c) < 32 for c in value)
            or not (parsed.scheme == "https" or parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"})):
        raise ValueError("Redirect URI must use HTTPS (HTTP allowed only for loopback), without credentials or fragments")
    return value


RedirectURI = Annotated[str, Field(min_length=1, max_length=2048), AfterValidator(validate_redirect)]
ClientText = Annotated[str, Field(min_length=1, max_length=100)]
GrantType = Literal["authorization_code", "client_credentials", "refresh_token"]


class OAuthClientCreate(BaseModel):
    client_name: ClientText
    redirect_uris: list[RedirectURI] = Field(max_length=50)
    allowed_scopes: list[ClientText] = Field(max_length=50)
    allowed_audiences: list[ClientText] = Field(max_length=50)
    grant_types: list[GrantType] = Field(default=["authorization_code", "client_credentials"], min_length=1, max_length=3)
    is_confidential: bool = True
    # Skip the consent screen. Only for clients operated by the Genesis owner.
    is_first_party: bool = False


class OAuthClientResponse(BaseModel):
    id: UUID
    client_name: str
    redirect_uris: list[str]
    allowed_scopes: list[str]
    allowed_audiences: list[str]
    grant_types: list[str]
    is_active: bool
    is_confidential: bool
    is_first_party: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OAuthClientWithSecret(OAuthClientResponse):
    client_secret: str  # Only returned on creation


class OAuthClientUpdate(BaseModel):
    client_name: Optional[ClientText] = None
    redirect_uris: Optional[list[RedirectURI]] = Field(None, max_length=50)
    allowed_scopes: Optional[list[ClientText]] = Field(None, max_length=50)
    allowed_audiences: Optional[list[ClientText]] = Field(None, max_length=50)
    grant_types: Optional[list[GrantType]] = Field(None, min_length=1, max_length=3)
    is_active: Optional[bool] = None
    is_first_party: Optional[bool] = None
