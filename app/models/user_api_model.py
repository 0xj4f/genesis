from pydantic import BaseModel, EmailStr, SecretStr, validator
from typing import Optional
import re
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr
    password: SecretStr
    disabled: Optional[bool] = False  # New field added with a default value

    @validator("password", pre=True, always=True)
    def validate_password(cls, password):
        if isinstance(password, SecretStr):
            password_str = password.get_secret_value()
        else:
            password_str = password

        # password_str = password.get_secret_value()
        if len(password_str) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if not re.search(r"[a-z]", password_str):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", password_str):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", password_str):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[@#$%^&+=!]", password_str):
            raise ValueError(
                "Password must contain at least one special character (@#$%^&+=!)"
            )
        return password


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: UUID
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[SecretStr] = None


class UserSearchRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


class UserDeleteResponse(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str or None = None


class GetTokenRequest(BaseModel):
    username: str
    password: str