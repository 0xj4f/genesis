from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator
from typing import Literal, Optional
from uuid import UUID
from datetime import datetime

from app.models.user_api_model import Username, _validated_secret


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
    must_change_password: bool = False
    password_expires_at: Optional[datetime] = None

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
    must_change_password: bool = False
    password_expires_at: Optional[datetime] = None
    # The open password-reset request for this user, if any.
    pending_request_id: Optional[UUID] = None
    pending_password_reset_at: Optional[datetime] = None


class RoleUpdateRequest(BaseModel):
    role: str


class UserStatusToggle(BaseModel):
    disabled: bool


class AdminUserCreate(BaseModel):
    username: Username
    email: EmailStr = Field(max_length=255)
    role: Literal["user", "admin"] = "user"
    # Omit to have Genesis generate a temporary password.
    password: Optional[SecretStr] = None
    require_password_change: bool = True
    # Admin-typed addresses are unproven: a verified address lets SSO sign-ins
    # with the same email link straight into the account.
    email_verified: bool = False

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, password):
        return None if password in (None, "") else _validated_secret(password)


class IssuedPassword(BaseModel):
    """Result of setting a password for someone else. temporary_password is the
    generated value, returned once; it is absent when the admin chose it."""
    message: str
    username: str
    role: str
    must_change_password: bool
    password_expires_at: Optional[datetime] = None
    temporary_password: Optional[str] = None


class AdminUserCreated(IssuedPassword):
    user: AdminUserListItem


class AccountRequestUser(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    auth_provider: str
    disabled: bool
    must_change_password: bool = False

    class Config:
        from_attributes = True


class AccountRequestItem(BaseModel):
    id: UUID
    category: str
    status: str
    request_count: int
    requester_ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    last_requested_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by_username: Optional[str] = None
    user: AccountRequestUser


class AccountRequestListResponse(BaseModel):
    requests: list[AccountRequestItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class AccountRequestSummary(BaseModel):
    open: int
