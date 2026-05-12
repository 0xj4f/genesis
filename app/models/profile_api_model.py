from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class ProfileBase(BaseModel):
    user_id: Optional[UUID] = None
    given_name: str
    family_name: str
    nick_name: Optional[str] = None
    email: Optional[EmailStr] = None
    sub: str
    date_of_birth: Optional[date] = None
    mobile_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    picture: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class Profile(ProfileBase):
    id: int
    phone_verified: Optional[bool] = False
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
    date_of_birth: Optional[date] = None
    mobile_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None


class PictureUploadResponse(BaseModel):
    picture: str
    picture_key: str
