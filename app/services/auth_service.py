from sqlalchemy.orm import Session
from app.utils.security import verify_password
from app.database.user_db_interface import get_user_by_username_db
from datetime import datetime, timedelta
import jwt
import os

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import HTTPException, status
from app.auth.auth import authenticate_user, create_access_token

ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES",30) # openssl rand -hex 32


def get_token_service(db: Session, form_data: dict ) -> dict :
    user = authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}



