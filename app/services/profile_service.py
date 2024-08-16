# from app.database.profile_db_interface import (
#     create_profile_db,
#     get_profile_by_id_db,
#     update_profile_by_id_db,
#     delete_profile_by_id_db,
#     get_profiles_db,
# )
# from app.models.profile_api_model import ProfileCreate, ProfileUpdate
# from sqlalchemy.orm import Session

# def create_profile_service(db: Session, profile_create: ProfileCreate):
#     return create_profile_db(db, profile_create)

# def get_profiles_service(db: Session):
#     return get_profiles_db(db)

# def get_profile_by_id_service(db: Session, profile_id: int):
#     return get_profile_by_id_db(db, profile_id)

# def update_profile_service(db: Session, profile_id: int, profile_update: ProfileUpdate):
#     return update_profile_by_id_db(db, profile_id, profile_update)

# def delete_profile_service(db: Session, profile_id: int):
#     return delete_profile_by_id_db(db, profile_id)
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

def create_profile_service(db: Session, profile_create: ProfileCreate):
    existing_profile = get_profile_by_user_db(db, profile_create.user_id)
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")

    return create_profile_db(db, profile_create)

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
