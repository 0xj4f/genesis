from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class AnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    native_count: int
    sso_count: int
    provider_breakdown: dict
    new_this_week: int
    admin_count: int


class AdminUserListItem(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    is_active: bool
    disabled: bool
    auth_provider: str
    is_native: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    last_login_method: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    users: list[AdminUserListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class AdminUserProfile(BaseModel):
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    date_of_birth: Optional[str] = None
    mobile_number: Optional[str] = None
    phone_verified: Optional[bool] = False
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    class Config:
        from_attributes = True


class LinkedProvider(BaseModel):
    provider: str
    provider_email: Optional[str] = None
    provider_username: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserDetail(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    is_active: bool
    disabled: bool
    auth_provider: str
    is_native: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    last_login_method: Optional[str] = None
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    profile: Optional[AdminUserProfile] = None
    sessions_count: int = 0
    linked_providers: list[LinkedProvider] = []


class RoleUpdateRequest(BaseModel):
    role: str


class UserStatusToggle(BaseModel):
    disabled: bool
