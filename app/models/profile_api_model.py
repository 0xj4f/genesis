from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class ProfileBase(BaseModel):
    user_id: Optional[UUID] = None
    given_name: str
    family_name: str
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    email: Optional[EmailStr] = None
    sub: str
    locale: Optional[str] = None
    timezone: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class Profile(ProfileBase):
    id: int
    picture_key: Optional[str] = None
    picture_updated_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    sub: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None


class PictureUploadResponse(BaseModel):
    picture: str
    picture_key: str
