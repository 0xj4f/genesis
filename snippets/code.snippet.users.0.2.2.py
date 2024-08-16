# ./app/auth/auth.py
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from app.database.user_db_interface import get_user_by_username_db
from app.models.user_api_model import User, Token, TokenData
from app.database.session import get_db
import bcrypt
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("OAUTH_SECRET_KEY","0f2883258b3c2cb9e21f1bdc827eafb9b7ad5509bf37103f82a1abab9109c65a") # openssl rand -hex 32
ALGORITHM = os.getenv("OAUTH_ALGORITHM","HS256") # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES", 30) # openssl rand -hex 32

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username_db(db, username)
    if not user or not verify_password(password, user.password):
        return False
    return user

def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(data: dict) -> str:
    return create_token(data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

def create_refresh_token(data: dict) -> str:
    return create_token(data, timedelta(days=7))  # Example: 7 days validity for refresh token

def decode_token(token: str) -> str:
    """
    to add more token validation in the future
    """
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def oauth_authenticate_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    - validate the token first
    - check if the user exist
    - check if the user is disabled 
    - return user db object 
    """
    print(f"token: {token}")
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    username: str = decode_token(token=token)
    print(token)
    print(username)
    try:
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
        user = get_user_by_username_db(db=db, username=token_data.username)
        print(f"db user: {user}")
    except JWTError:
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise HTTPException(status_code=400, detail="User is deactivated")
    return user

"""
test scripts


- create user 
{
    username: disabled
    email: disabled@dev.com
    password: HelloWorld123!
} print if existing and make it ok
- update user disabled = True
- get user by user id, check if disabled and print
- test /token endpoint for login
- test /user/me, response should be raise HTTPException(status_code=400, detail="User is deactivated")

"""
# ./app/routes/profiles.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.profile_service import (
    create_profile_service,
    get_profiles_service,
    get_profile_by_id_service,
    update_profile_service,
    delete_profile_service,
)
from app.models.profile_api_model import ProfileCreate, Profile, ProfileUpdate

router = APIRouter()

@router.post("/", response_model=Profile)
def create_profile(profile_create: ProfileCreate, db: Session = Depends(get_db)):
    return create_profile_service(db, profile_create)

@router.get("/", response_model=list[Profile])
def get_profiles(db: Session = Depends(get_db)):
    return get_profiles_service(db)

@router.get("/{profile_id}", response_model=Profile)
def get_profile_by_id(profile_id: int, db: Session = Depends(get_db)):
    profile = get_profile_by_id_service(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/{profile_id}", response_model=Profile)
def update_profile(profile_id: int, profile_update: ProfileUpdate, db: Session = Depends(get_db)):
    return update_profile_service(db, profile_id, profile_update)

@router.delete("/{profile_id}", response_model=dict)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    if delete_profile_service(db, profile_id):
        return {"message": f"Profile with ID {profile_id} has been successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="Profile not found")

# ./app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status,Form
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.auth_service import get_token_service, refresh_access_token_service
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from app.models.user_api_model import (
    Token
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/token", tags=["auth"], response_model=Token)
def get_token_endpoint(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return get_token_service(
        db=db,
        form_data=form_data,
    )


@router.post("/refresh_token", tags=["auth"], response_model=Token)
def refresh_token_endpoint(refresh_token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return refresh_access_token_service(refresh_token=refresh_token, db=db)
# ./app/routes/users.py
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
# from app.auth.auth import get_current_user
from app.auth.auth import oauth_authenticate_current_user

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

# ===========================================================================
# AUTHENTICATED ROUTES 
# ===========================================================================
"""
important notes in authenticated routes.
make sure that defined endpoints ends with "/"
example:
/user/me -> /users/me/
otherwise authentication process gets errors 
"""
from app.auth.auth import oauth_authenticate_current_user

@router.get("/me/", response_model=User)
def read_users_me(current_user: dict = Depends(oauth_authenticate_current_user)):
# def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
# ./app/utils/security.py
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

# ./app/utils/helpers.py

# ./app/models/__init__.py
from app.models.user_db_model import User
from app.models.profile_db_model import Profile

# ./app/models/profile_db_model.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from uuid import uuid4

Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)  # You can change to UUID if preferred
    user_id = Column(CHAR(36), ForeignKey('users.id'), nullable=False)
    given_name = Column(String(100), nullable=False)
    family_name = Column(String(100), nullable=False)
    nick_name = Column(String(100), nullable=True)
    picture = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    email = Column(String(255), unique=True, nullable=False)
    sub = Column(String(255), nullable=False)

    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id}, email={self.email})>"

# ./app/models/profile_api_model.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProfileBase(BaseModel):
    user_id: UUID
    given_name: str
    family_name: str
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    email: EmailStr
    sub: str

class ProfileCreate(ProfileBase):
    pass

class Profile(ProfileBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ProfileUpdate(BaseModel):
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    email: Optional[EmailStr] = None
    sub: Optional[str] = None

# ./app/models/user_db_model.py
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

# ./app/models/user_api_model.py
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


# class Token(BaseModel):
#     access_token: str
#     token_type: str

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str  # New field added


class TokenData(BaseModel):
    username: str or None = None


class GetTokenRequest(BaseModel):
    username: str
    password: str
# ./app/database/user_db_interface.py
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

# ./app/database/profile_db_interface.py
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

# ./app/database/session.py
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
# ./app/main.py
from fastapi import FastAPI
from sqlalchemy.ext.declarative import declarative_base
from app.routes.users import router as user_router
from app.routes.profiles import router as profile_router
from app.routes.auth import router as auth_router
from app.database.session import Base,engine
# import app.models  # This ensures that all models are imported and registered with SQLAlchemy
from app.models.user_db_model import User
from app.models.profile_db_model import Profile
import logging

app = FastAPI(title="Genesis - Identity Access Management")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Log the creation of tables
logger.info("Creating tables...")
Base.metadata.create_all(bind=engine)
logger.info("Tables created.")

# Include routers
app.include_router(auth_router, prefix="", tags=["auth"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])
# ./app/services/user_service.py
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

# ./app/services/profile_service.py
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

# ./app/services/auth_service.py
from sqlalchemy.orm import Session
from app.utils.security import verify_password
from app.database.user_db_interface import get_user_by_username_db
from datetime import datetime, timedelta
import jwt
import os

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import HTTPException, status
from app.auth.auth import authenticate_user, create_access_token, create_refresh_token, decode_token
from app.models.user_api_model import Token


def get_token_service(db: Session, form_data: dict ) -> Token :
    user = authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.username})
    # Generate refresh token
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def refresh_access_token_service(refresh_token: str, db: Session) -> Token:
    username = decode_token(refresh_token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch the user from the database
    user = get_user_by_username_db(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is deactivated",
        )

    # Generate new access and refresh tokens
    access_token = create_access_token(data={"sub": username})
    refresh_token = create_refresh_token(data={"sub": username})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

