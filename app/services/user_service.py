from app.database.user_db_interface import (
    create_user_db,
    get_all_users_db,
    get_user_by_id_db,
    update_user_by_id_db,
    delete_user_by_id_db,
    get_user_by_email_db,
    get_user_by_username_db
)
from app.models.user_api_model import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from app.utils.security import verify_password, hash_password
from app.models.user_api_model import (
    UserCreate,
    User,
    UserSearchRequest,
    UserUpdate,
    UserDeleteResponse,
    Token,
    TokenData,
)
from fastapi import HTTPException

def validate_existing_user(db: Session, email: str = None, username: str = None):
    """
    Validates that the email or username does not already exist in the database.

    Args:
    - db (Session): Database session to use for the query.
    - email (str, optional): Email to check against existing records.
    - username (str, optional): Username to check against existing records.

    Raises:
    - HTTPException: If the email or username already exists.
    """
    if email and get_user_by_email_db(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if username and get_user_by_username_db(db, username):
        raise HTTPException(status_code=400, detail="Username already taken")

def create_user_service(db: Session, user_create: UserCreate) -> User:
    # Additional business logic can be added here
    validate_existing_user(db, email=user_create.email, username=user_create.username)
    user_create.password = hash_password(user_create.password.get_secret_value())  # Hash password
    return create_user_db(db, user_create)

def get_all_users_service(db: Session):
    return get_all_users_db(db)

def get_user_by_id_service(db: Session, user_id: str):
    return get_user_by_id_db(db, user_id)

def update_user_service(db: Session, user_id: str, user_update: UserUpdate):
    if user_update.password:
        user_update.password = hash_password(user_update.password.get_secret_value())
        
    validate_existing_user(db, email=user_update.email, username=user_update.username)
    return update_user_by_id_db(db, user_id, user_update)

def delete_user_service(db: Session, user_id: str):
    return delete_user_by_id_db(db, user_id)

def get_user_by_email_service(db: Session, email: str):
    return get_user_by_email_db(db, email)

def get_user_by_username_service(db: Session, username: str):
    return get_user_by_username_db(db, username)
