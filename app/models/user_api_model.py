from pydantic import BaseModel, EmailStr, SecretStr, Field, AfterValidator, field_validator
from typing import Annotated
from typing import Optional
import re
from uuid import UUID
from datetime import datetime


PASSWORD_MIN_LENGTH = 12
# Argon2id has no input-length limit (bcrypt's was 72 bytes); this cap only
# bounds the work an attacker can request per hash.
PASSWORD_MAX_LENGTH = 128


def validate_password_strength(password_str: str) -> str:
    if len(password_str) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters long")
    if len(password_str) < PASSWORD_MIN_LENGTH:
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


def _validated_secret(password):
    password_str = password.get_secret_value() if isinstance(password, SecretStr) else str(password)
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
    # True when an email change waits for the new address to be verified.
    email_change_pending: bool = False

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[Username] = None
    email: Optional[EmailStr] = Field(None, max_length=255)
    # Required when changing your own email (re-authentication).
    current_password: Optional[SecretStr] = None
    # No longer accepted here; the route rejects it with a pointer to
    # POST /users/me/password, which requires the current password.
    password: Optional[SecretStr] = None


class PasswordChangeRequest(BaseModel):
    # Optional only for SSO-only accounts setting their first password.
    current_password: Optional[SecretStr] = None
    new_password: SecretStr

    @field_validator("new_password", mode="before")
    @classmethod
    def validate_new_password(cls, password):
        return _validated_secret(password)


class AdminPasswordReset(BaseModel):
    new_password: SecretStr

    @field_validator("new_password", mode="before")
    @classmethod
    def validate_new_password(cls, password):
        return _validated_secret(password)


class EmailVerifyRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class EmailResendRequest(BaseModel):
    email: EmailStr = Field(max_length=255)


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
