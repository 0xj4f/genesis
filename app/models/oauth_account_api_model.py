from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class OAuthAccountResponse(BaseModel):
    id: UUID
    provider: str
    provider_email: Optional[str] = None
    provider_username: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OAuthAccountListResponse(BaseModel):
    accounts: list[OAuthAccountResponse]
