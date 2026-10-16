from pydantic import BaseModel, EmailStr, SecretStr, Field, AfterValidator, field_validator
from typing import Annotated
from typing import Optional
import re
from uuid import UUID
from datetime import datetime


def validate_password_strength(password_str: str) -> str:
    if len(password_str.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    if len(password_str) < 12:
        raise ValueError("Password must be at least 12 characters long")
    if not re.search(r"[a-z]", password_str):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[A-Z]", password_str):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", password_str):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[@#$%^&+=!]", password_str):
        raise ValueError("Password must contain at least one special character (@#$%^&+=!)")
    return password_str


def validate_username(value: str) -> str:
    if not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Username must be nonblank and contain no control characters")
    return value


Username = Annotated[str, Field(min_length=1, max_length=100), AfterValidator(validate_username)]


class UserBase(BaseModel):
    username: Username
    email: EmailStr = Field(max_length=255)
    password: Optional[SecretStr] = None  # Nullable for SSO users
    disabled: Optional[bool] = False

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, password):
        if password is None:
            return password
        if isinstance(password, SecretStr):
            password_str = password.get_secret_value()
        else:
            password_str = str(password)
        validate_password_strength(password_str)
        return password


class UserCreate(BaseModel):
    username: Username
    email: EmailStr = Field(max_length=255)
    password: SecretStr

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, password):
        if isinstance(password, SecretStr):
            password_str = password.get_secret_value()
        else:
            password_str = str(password)
        validate_password_strength(password_str)
        return password


class User(BaseModel):
    id: UUID
    username: str
    # Responses must serialize legacy/internal addresses (e.g. the seeded
    # adam@genesis.local). Create/update requests still validate EmailStr.
    email: str
    disabled: Optional[bool] = False
    is_active: Optional[bool] = True
    email_verified: Optional[bool] = False
    auth_provider: Optional[str] = "native"
    is_native: Optional[bool] = True
    last_login_at: Optional[datetime] = None
    last_login_method: Optional[str] = None
    role: Optional[str] = "user"
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[Username] = None
    email: Optional[EmailStr] = Field(None, max_length=255)
    password: Optional[SecretStr] = None

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, password):
        if password is None:
            return password
        if isinstance(password, SecretStr):
            password_str = password.get_secret_value()
        else:
            password_str = str(password)
        validate_password_strength(password_str)
        return password


class UserSearchRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


class UserDeleteResponse(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    id_token: Optional[str] = None  # For OIDC flows


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None


class GetTokenRequest(BaseModel):
    username: str
    password: str


class UserMinimal(BaseModel):
    user_id: UUID
    username: str
