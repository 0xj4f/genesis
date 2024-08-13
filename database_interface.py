from sqlalchemy.orm import Session
from models import User
from uuid import UUID


# Create a new user
def create_user(
    db: Session,
    username: str,
    email: str,
    hashed_password: str,
    is_active: bool = True,
    is_superuser: bool = False,
    oauth_provider: str = None,
    oauth_id: str = None,
):
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_active=is_active,
        is_superuser=is_superuser,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Retrieve all users
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


# Retrieve a single user by ID
def get_user_by_id(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == str(user_id)).first()


# Update a user by ID
def update_user(
    db: Session,
    user_id: UUID,
    username: str = None,
    email: str = None,
    hashed_password: str = None,
    is_active: bool = None,
    is_superuser: bool = None,
    oauth_provider: str = None,
    oauth_id: str = None,
):
    db_user = db.query(User).filter(User.id == str(user_id)).first()
    if db_user is None:
        return None

    if username is not None:
        db_user.username = username
    if email is not None:
        db_user.email = email
    if hashed_password is not None:
        db_user.hashed_password = hashed_password
    if is_active is not None:
        db_user.is_active = is_active
    if is_superuser is not None:
        db_user.is_superuser = is_superuser
    if oauth_provider is not None:
        db_user.oauth_provider = oauth_provider
    if oauth_id is not None:
        db_user.oauth_id = oauth_id

    db.commit()
    db.refresh(db_user)
    return db_user


# Delete a user by ID
def delete_user(db: Session, user_id: UUID):
    db_user = db.query(User).filter(User.id == str(user_id)).first()
    if db_user is None:
        return None
    db.delete(db_user)
    db.commit()
    return db_user
