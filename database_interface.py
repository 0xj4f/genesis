from sqlalchemy.orm import Session
from database_models import User
from api_models import UserCreate


def create_user(db: Session, user_create: UserCreate):
    db_user = User(
        username=user_create.username,
        email=user_create.email,
        password=user_create.password.get_secret_value(),  # For security reasons, store the raw password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_users(db: Session):
    return db.query(User).all()


def get_user_by_id(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()
