from typing import Optional

from pydantic import BaseModel


class ProfileUpsertRequest(BaseModel):
    given_name: str
    family_name: str
    nick_name: Optional[str] = None
    picture_url: Optional[str] = None
    locale: Optional[str] = None


class ProfileResponse(BaseModel):
    user_id: str
    given_name: str
    family_name: str
    nick_name: Optional[str] = None
    picture_url: Optional[str] = None
    locale: Optional[str] = None

    class Config:
        orm_mode = True
