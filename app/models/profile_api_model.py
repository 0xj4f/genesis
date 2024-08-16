from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProfileBase(BaseModel):
    user_id: Optional[UUID]
    given_name: str
    family_name: str
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    email: Optional[EmailStr]
    sub: str

class ProfileCreate(ProfileBase):
    pass

class Profile(ProfileBase):
    id: int
    
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ProfileUpdate(BaseModel):
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    sub: Optional[str] = None
