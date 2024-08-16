# ./app/routes/profiles.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.profile_service import (
    create_profile_service,
    get_profiles_service,
    get_profile_by_id_service,
    update_profile_service,
    delete_profile_service,
)
from app.models.profile_api_model import ProfileCreate, Profile, ProfileUpdate

router = APIRouter()

@router.post("/", response_model=Profile)
def create_profile(profile_create: ProfileCreate, db: Session = Depends(get_db)):
    return create_profile_service(db, profile_create)

@router.get("/", response_model=list[Profile])
def get_profiles(db: Session = Depends(get_db)):
    return get_profiles_service(db)

@router.get("/{profile_id}", response_model=Profile)
def get_profile_by_id(profile_id: int, db: Session = Depends(get_db)):
    profile = get_profile_by_id_service(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/{profile_id}", response_model=Profile)
def update_profile(profile_id: int, profile_update: ProfileUpdate, db: Session = Depends(get_db)):
    return update_profile_service(db, profile_id, profile_update)

@router.delete("/{profile_id}", response_model=dict)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    if delete_profile_service(db, profile_id):
        return {"message": f"Profile with ID {profile_id} has been successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="Profile not found")

# ./app/models/profile_db_model.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from uuid import uuid4
from app.database.session import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)  # You can change to UUID if preferred
    user_id = Column(CHAR(36), ForeignKey('users.id'), nullable=False)
    given_name = Column(String(100), nullable=False)
    family_name = Column(String(100), nullable=False)
    nick_name = Column(String(100), nullable=True)
    picture = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    email = Column(String(255), unique=True, nullable=False)
    sub = Column(String(255), nullable=False)

    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id}, email={self.email})>"

# ./app/models/profile_api_model.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProfileBase(BaseModel):
    user_id: UUID
    given_name: str
    family_name: str
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    email: EmailStr
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
    email: Optional[EmailStr] = None
    sub: Optional[str] = None

# ./app/database/profile_db_interface.py
from app.models.profile_db_model import Profile
from app.models.profile_api_model import ProfileCreate, ProfileUpdate
from sqlalchemy.orm import Session

def create_profile_db(db: Session, profile_create: ProfileCreate) -> Profile:
    db_profile = Profile(**profile_create.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def get_profile_by_id_db(db: Session, profile_id: int) -> Profile:
    return db.query(Profile).filter(Profile.id == profile_id).first()

def update_profile_by_id_db(db: Session, profile_id: int, profile_update: ProfileUpdate) -> Profile:
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        return None
    for var, value in vars(profile_update).items():
        setattr(profile, var, value) if value else None
    db.commit()
    db.refresh(profile)
    return profile

def delete_profile_by_id_db(db: Session, profile_id: int):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        return None
    db.delete(profile)
    db.commit()
    return profile

def get_profiles_db(db: Session):
    return db.query(Profile).all()

# ./app/services/profile_service.py
from app.database.profile_db_interface import (
    create_profile_db,
    get_profile_by_id_db,
    update_profile_by_id_db,
    delete_profile_by_id_db,
    get_profiles_db,
)
from app.models.profile_api_model import ProfileCreate, ProfileUpdate
from sqlalchemy.orm import Session

def create_profile_service(db: Session, profile_create: ProfileCreate):
    return create_profile_db(db, profile_create)

def get_profiles_service(db: Session):
    return get_profiles_db(db)

def get_profile_by_id_service(db: Session, profile_id: int):
    return get_profile_by_id_db(db, profile_id)

def update_profile_service(db: Session, profile_id: int, profile_update: ProfileUpdate):
    return update_profile_by_id_db(db, profile_id, profile_update)

def delete_profile_service(db: Session, profile_id: int):
    return delete_profile_by_id_db(db, profile_id)

