from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class SessionBase(BaseModel):
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_name: Optional[str] = None
    login_method: str = "password"


class SessionResponse(BaseModel):
    id: UUID
    ip_address: Optional[str] = None
    device_name: Optional[str] = None
    login_method: str
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    is_current: bool = False

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
