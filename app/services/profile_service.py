# ./app/services/profile_service.py
from app.database.profile_db_interface import (
    create_profile_db,
    get_profile_by_user_db,
    update_profile_by_id_db,
    delete_profile_by_user_db,
)
from fastapi import HTTPException
from app.models.profile_api_model import ProfileCreate, ProfileUpdate
from sqlalchemy.orm import Session
from app.models.user_db_model import User
from app.models.profile_db_model import Profile

def create_profile_service(db: Session, user, profile_create: ProfileCreate):
    user_id = str(user.id)
    db.query(User).filter(User.id == user_id).with_for_update().first()
    existing_profile = db.query(Profile).filter(Profile.user_id == user_id).with_for_update().first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")

    # Identity fields come from the authenticated user, never from the request.
    return create_profile_db(db, {**profile_create.model_dump(), "user_id": user_id, "email": user.email, "sub": user_id})

def get_profile_by_user_service(db: Session, user_id: str):
    profile = get_profile_by_user_db(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

def update_profile_service(db: Session, user_id: str, profile_update: ProfileUpdate):
    profile = update_profile_by_id_db(db, user_id, profile_update)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

def delete_profile_service(db: Session, user_id: str):
    profile_deleted = delete_profile_by_user_db(db, user_id)
    if not profile_deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile_deleted
