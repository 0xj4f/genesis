from pydantic import BaseModel, Field, AfterValidator
from typing import Optional, Annotated
from uuid import UUID
from datetime import datetime, date


def validate_birth_date(value: date) -> date:
    if value > date.today():
        raise ValueError("Date of birth cannot be in the future")
    return value


Name = Annotated[str, Field(max_length=100)]
ShortText = Annotated[str, Field(max_length=20)]
Address = Annotated[str, Field(max_length=255)]
BirthDate = Annotated[date, AfterValidator(validate_birth_date)]


class ProfileFields(BaseModel):
    """Fields a user may set on their own profile.

    user_id, email, sub and picture are server-controlled: sub is always the
    user's id, and picture changes only through the upload endpoint or the SSO
    import (an arbitrary URL would make every viewer's browser fetch it).
    Unknown fields sent by clients are ignored.
    """
    given_name: Name
    family_name: Name
    nick_name: Optional[Name] = None
    date_of_birth: Optional[BirthDate] = None
    mobile_number: Optional[ShortText] = None
    address_line1: Optional[Address] = None
    address_line2: Optional[Address] = None
    city: Optional[Name] = None
    state: Optional[Name] = None
    zip_code: Optional[ShortText] = None
    country: Optional[Name] = None


class ProfileCreate(ProfileFields):
    pass


class Profile(ProfileFields):
    id: int
    user_id: Optional[UUID] = None
    email: Optional[str] = None  # Serialize stored/internal addresses in responses.
    sub: Optional[str] = None
    picture: Optional[str] = None
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
