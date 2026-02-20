from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, SecretStr, validator

from app.models.user_db_model import AuthProvider, UserRole, UserStatus


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: SecretStr

    @validator("password", pre=True, always=True)
    def validate_password(cls, password):
        value = password.get_secret_value() if isinstance(password, SecretStr) else password
        if len(value) < 12:
            raise ValueError("Password must be at least 12 characters long")
        return password


class LoginRequest(BaseModel):
    username_or_email: str
    password: SecretStr


class OAuthCallbackRequest(BaseModel):
    provider_user_id: str
    email: Optional[EmailStr] = None
    email_verified: bool = False
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture_url: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserMeResponse(BaseModel):
    id: str
    role: UserRole
    status: UserStatus
    created_at: datetime

    class Config:
        orm_mode = True


class UserMeUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class AdminUserUpdateRequest(BaseModel):
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class AdminUserListItem(BaseModel):
    id: str
    role: UserRole
    status: UserStatus
    created_at: datetime


class SessionItem(BaseModel):
    id: str
    user_id: str
    identity_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None


class AuditLogItem(BaseModel):
    id: str
    actor_user_id: str
    action: str
    target_type: str
    target_id: Optional[str]
    metadata_json: dict
    created_at: datetime
