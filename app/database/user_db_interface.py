from app.models.user_db_model import User
from app.models.user_api_model import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from uuid import UUID

# def create_user_db(db: Session, user_payload: dict) -> User:
#     db_user = User(**user_payload)
#     db.add(db_user); 
#     db.commit(); 
#     db.refresh(db_user)
#     return db_user

def create_user_db(db: Session, user_create: UserCreate) -> User:
    db_user = User(**user_create.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_all_users_db(db: Session):
    return db.query(User).all()

def get_user_by_id_db(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()

def update_user_by_id_db(db: Session, user_id: str, user_update: UserUpdate):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    for var, value in vars(user_update).items():
        setattr(user, var, value) if value else None
    db.commit()
    db.refresh(user)
    return user

def delete_user_by_id_db(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    db.delete(user)
    db.commit()
    return user

def get_user_by_email_db(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username_db(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()
