from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database_config import SessionLocal, engine
from database_models import Base
from database_interface import (
    create_user,
    get_all_users,
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    update_user_by_id,
    delete_user_by_id,
)
from api_models import (
    UserCreate,
    User,
    UserSearchRequest,
    UserUpdate,
    UserDeleteResponse,
)
import logging

app = FastAPI()
logging.basicConfig(level=logging.DEBUG)

# Create the database tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# USERS ENDPOINTS
@app.post("/users/", response_model=User)
def create_user_endpoint(user_create: UserCreate, db: Session = Depends(get_db)):
    # Validate if the email already exists
    if get_user_by_email(db, email=user_create.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate if the username already exists
    if get_user_by_username(db, username=user_create.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create and return the new user
    db_user = create_user(db=db, user_create=user_create)
    return db_user


@app.get("/users/", response_model=list[User])
def get_users_endpoint(db: Session = Depends(get_db)):
    try:
        users = get_all_users(db)
        return users
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/users/{user_id}", response_model=User)
def get_user_by_id_endpoint(user_id: str, db: Session = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users/search", response_model=User)
async def get_user_by_request(
    request: UserSearchRequest, db: Session = Depends(get_db)
):
    if request.email:
        user = get_user_by_email(db, email=request.email)
        if user:
            return user
        raise HTTPException(
            status_code=404, detail="User with the provided email not found"
        )

    if request.username:
        user = get_user_by_username(db, username=request.username)
        if user:
            return user
        raise HTTPException(
            status_code=404, detail="User with the provided username not found"
        )

    raise HTTPException(
        status_code=400, detail="Either email or username must be provided"
    )


@app.put("/users/{user_id}", response_model=User)
async def update_user_endpoint(
    user_id: str, user_update: UserUpdate, db: Session = Depends(get_db)
):
    db_user = get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the email is being updated and already exists for another user
    if user_update.email and user_update.email != db_user.email:
        existing_user = get_user_by_email(db, email=user_update.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

    # Check if the username is being updated and already exists for another user
    if user_update.username and user_update.username != db_user.username:
        existing_user = get_user_by_username(db, username=user_update.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")

    updated_user = update_user_by_id(db=db, user_id=user_id, user_update=user_update)
    return updated_user


@app.delete("/users/{user_id}", response_model=UserDeleteResponse)
async def delete_user_endpoint(user_id: str, db: Session = Depends(get_db)):
    # Get the user by ID
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        # Delete the user
        delete_user_by_id(db, user_id)
        return {"message": f"User with ID {user_id} has been successfully deleted"}
    except SQLAlchemyError as e:
        # Handle database-related errors
        db.rollback()  # Rollback the transaction
        raise HTTPException(
            status_code=500, detail="An error occurred while deleting the user"
        )


## AUTHENTICATION 

import bcrypt
import jwt
from datetime import datetime, timedelta

# Configuration
SECRET_KEY = "0f2883258b3c2cb9e21f1bdc827eafb9b7ad5509bf37103f82a1abab9109c65a" # openssl rand -hex 32
ALGORITHM = "HS256"  # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expiration time

# Password verification function
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/login/")
def login_endpoint(email: str, password: str, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email=email)
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}



