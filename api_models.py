from pydantic import BaseModel, EmailStr, SecretStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr
    password: SecretStr


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: UUID
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    class Config:
        orm_mode = True
