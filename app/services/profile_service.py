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
