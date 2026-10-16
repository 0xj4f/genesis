from app.database.user_db_interface import (
    create_user_db,
    get_all_users_db,
    get_user_by_id_db,
    update_user_by_id_db,
    delete_user_by_id_db,
    get_user_by_email_db,
    get_user_by_username_db,
)
from app.models.user_api_model import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from app.utils.security import hash_password
from fastapi import HTTPException


def validate_existing_user(db: Session, email: str = None, username: str = None, exclude_user_id: str = None):
    email_user = get_user_by_email_db(db, email) if email else None
    username_user = get_user_by_username_db(db, username) if username else None
    if email_user and str(email_user.id) != exclude_user_id:
        raise HTTPException(status_code=400, detail="Email already registered")
    if username_user and str(username_user.id) != exclude_user_id:
        raise HTTPException(status_code=400, detail="Username already taken")


def create_user_service(db: Session, user_create: UserCreate):
    validate_existing_user(db, email=user_create.email, username=user_create.username)
    user_create.password = hash_password(user_create.password.get_secret_value())
    return create_user_db(db, user_create)


def get_all_users_service(db: Session):
    return get_all_users_db(db)


def get_user_by_id_service(db: Session, user_id: str, for_update: bool = False):
    return get_user_by_id_db(db, user_id, for_update=for_update)


def update_user_service(db: Session, user_id: str, user_update: UserUpdate):
    if user_update.password:
        user_update.password = hash_password(user_update.password.get_secret_value())
    validate_existing_user(db, email=user_update.email, username=user_update.username, exclude_user_id=str(user_id))
    return update_user_by_id_db(db, user_id, user_update)


def delete_user_service(db: Session, user_id: str):
    return delete_user_by_id_db(db, user_id)


def get_user_by_email_service(db: Session, email: str):
    return get_user_by_email_db(db, email)


def get_user_by_username_service(db: Session, username: str):
    return get_user_by_username_db(db, username)
