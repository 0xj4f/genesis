# app/main.py
from fastapi import FastAPI
from sqlalchemy.ext.declarative import declarative_base
from app.routes.users import router as user_router

app = FastAPI()
# Include routers
app.include_router(user_router, prefix="/users", tags=["users"])

# app/auth/auth.py
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import bcrypt
import jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# app/database/user_db_interface.py
from app.models.user_db_model import User
from app.models.user_api_model import UserCreate, UserUpdate
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

# app/database/session.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os

DATABASE_USER = os.getenv("MYSQL_DEV_USER", "root")
DATABASE_PASSWORD = os.getenv("MYSQL_DEV_PASSWORD", "")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
DATABASE_NAME = os.getenv("DATABASE_NAME", "genesis")
encoded_password = quote_plus(DATABASE_PASSWORD)  # if password has special characters

# Construct the database URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{encoded_password}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

print(SQLALCHEMY_DATABASE_URL)
# Create the engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# app/models/user_api_model.py
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

# app/models/user_db_model.py
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

# app/routes/users.py
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
from app.models.user_api_model import UserCreate, User, UserUpdate, UserDeleteResponse, UserSearchRequest

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

# app/routes/profiles.py

# app/services/user_service.py
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

# app/services/profile_service.py

# app/utils/security.py
import bcrypt

def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt.
    
    Args:
    - password (str): Plain text password to hash.

    Returns:
    - str: A bcrypt hashed password.
    """
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a hashed password.

    Args:
    - plain_password (str): Plain text password to verify.
    - hashed_password (str): Bcrypt hashed password to verify against.

    Returns:
    - bool: True if verification is successful, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# app/utils/helpers.py

