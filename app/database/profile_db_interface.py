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
