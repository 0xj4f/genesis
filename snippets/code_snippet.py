# app/main.py
from fastapi import FastAPI
from sqlalchemy.ext.declarative import declarative_base
from app.database.database_config import engine
from app.routes.users import router as user_router

app = FastAPI()

app.include_router(user_router, prefix="/users", tags=["users"])


# app/routes/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.user_service import (
    create_user_service,
    get_all_users_service,
    get_user_by_id_service,
    update_user_service,
    delete_user_service,
    get_user_by_username_service,
    get_user_by_email_service
)
from app.models.api_models import UserCreate, User, UserUpdate, UserDeleteResponse, UserSearchRequest

router = APIRouter()

@router.post("/", response_model=User)
def create_user(user_create: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user_service(db, user_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[User])
def get_users(db: Session = Depends(get_db)):
    return get_all_users_service(db)

@router.get("/{user_id}", response_model=User)
def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    user = get_user_by_id_service(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=User)
def update_user(user_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    try:
        return update_user_service(db, user_id, user_update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}", response_model=UserDeleteResponse)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    if delete_user_service(db, user_id):
        return {"message": f"User with ID {user_id} has been successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.post("/search", response_model=User)
def search_user(request: UserSearchRequest, db: Session = Depends(get_db)):
    user = None
    if request.email:
        user = get_user_by_email_service(db, request.email)
    elif request.username:
        user = get_user_by_username_service(db, request.username)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")



# app/services/user_service.py
from app.database.database_interface import (
    create_user_db,
    get_all_users_db,
    get_user_by_id_db,
    update_user_by_id_db,
    delete_user_by_id_db,
    get_user_by_email_db,
    get_user_by_username_db
)
from app.models.api_models import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from app.utils.security import verify_password, hash_password
from app.models.api_models import (
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

# app/database/database_interface.py
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

# app/models/api_models.py
from pydantic import BaseModel, EmailStr, SecretStr, validator
from typing import Optional
import re
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr
    password: SecretStr
    disabled: Optional[bool] = False  # New field added with a default value

    @validator("password", pre=True, always=True)
    def validate_password(cls, password):
        if isinstance(password, SecretStr):
            password_str = password.get_secret_value()
        else:
            password_str = password

        # password_str = password.get_secret_value()
        if len(password_str) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if not re.search(r"[a-z]", password_str):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", password_str):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", password_str):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[@#$%^&+=!]", password_str):
            raise ValueError(
                "Password must contain at least one special character (@#$%^&+=!)"
            )
        return password


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: UUID
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[SecretStr] = None


class UserSearchRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


class UserDeleteResponse(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str or None = None

# app/models/database_models.py
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String as SqlString
from sqlalchemy.sql import func
from uuid import uuid4
import sqlalchemy as sa

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(SqlString(100), unique=True, nullable=False)
    email = Column(SqlString(255), unique=True, nullable=False)
    password = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_modified = Column(DateTime, onupdate=func.now(), default=func.now())
    disabled = Column(Boolean, nullable=False, default=False)  # New field

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
