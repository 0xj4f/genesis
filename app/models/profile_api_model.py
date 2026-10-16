from pydantic import BaseModel, EmailStr, Field, AfterValidator
from typing import Optional, Annotated
from urllib.parse import urlsplit
from uuid import UUID
from datetime import datetime, date


def validate_picture_url(value: str) -> str:
    parsed = urlsplit(value)
    if any(ord(c) < 32 for c in value) or not (
        value.startswith("/avatars/") and not value.startswith("//")
        or parsed.scheme in {"http", "https"} and parsed.netloc and not parsed.username and not parsed.password
    ):
        raise ValueError("Picture must be an HTTP(S) URL or local avatar path")
    return value


def validate_birth_date(value: date) -> date:
    if value > date.today():
        raise ValueError("Date of birth cannot be in the future")
    return value


Name = Annotated[str, Field(max_length=100)]
ShortText = Annotated[str, Field(max_length=20)]
Address = Annotated[str, Field(max_length=255)]
PictureURL = Annotated[str, Field(max_length=255), AfterValidator(validate_picture_url)]
BirthDate = Annotated[date, AfterValidator(validate_birth_date)]


class ProfileBase(BaseModel):
    user_id: Optional[UUID] = None
    given_name: Name
    family_name: Name
    nick_name: Optional[Name] = None
    email: Optional[EmailStr] = Field(None, max_length=255)
    sub: str = Field(max_length=255)
    date_of_birth: Optional[BirthDate] = None
    mobile_number: Optional[ShortText] = None
    address_line1: Optional[Address] = None
    address_line2: Optional[Address] = None
    city: Optional[Name] = None
    state: Optional[Name] = None
    zip_code: Optional[ShortText] = None
    country: Optional[Name] = None
    picture: Optional[PictureURL] = None


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
    given_name: Optional[Name] = None
    family_name: Optional[Name] = None
    nick_name: Optional[Name] = None
    picture: Optional[PictureURL] = None
    sub: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[BirthDate] = None
    mobile_number: Optional[ShortText] = None
    address_line1: Optional[Address] = None
    address_line2: Optional[Address] = None
    city: Optional[Name] = None
    state: Optional[Name] = None
    zip_code: Optional[ShortText] = None
    country: Optional[Name] = None


class PictureUploadResponse(BaseModel):
    picture: str
    picture_key: str
