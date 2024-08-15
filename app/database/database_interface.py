# from sqlalchemy.orm import Session
# from app.models.database_models import User
# from app.models.api_models import UserCreate
# from app.models.api_models import UserCreate, UserUpdate
# from uuid import UUID
# import bcrypt


# def hash_password(password: str) -> str:
#     # Hash the password with bcrypt
#     hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
#     return hashed_password.decode("utf-8")


# def create_user(db: Session, user_create: UserCreate) -> User:
#     hashed_password = hash_password(user_create.password.get_secret_value())

#     db_user = User(
#         username=user_create.username, email=user_create.email, password=hashed_password
#     )
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user


# def get_all_users(db: Session):
#     return db.query(User).all()


# def get_user_by_id(db: Session, user_id: UUID):
#     return db.query(User).filter(User.id == user_id).first()


# def get_user_by_email(db: Session, email: str):
#     return db.query(User).filter(User.email == email).first()


# def get_user_by_username(db: Session, username: str):
#     return db.query(User).filter(User.username == username).first()


# def update_user_by_id(db: Session, user_id: UUID, user_update: UserUpdate):
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         return None

#     if user_update.username:
#         user.username = user_update.username
#     if user_update.email:
#         user.email = user_update.email
#     if user_update.password:
#         user.password = user_update.password.get_secret_value()

#     db.commit()
#     db.refresh(user)
#     return user


# def delete_user_by_id(db: Session, user_id: UUID):
#     user = db.query(User).filter(User.id == user_id).first()
#     if user is None:
#         return None

#     db.delete(user)
#     db.commit()
#     return user
from app.models.database_models import User
from app.models.api_models import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from uuid import UUID

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
