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
    
    payload = {
            "sub": user.username,
            "user_id": user.id
    }
    access_token = create_access_token(data=payload)
    refresh_token = create_refresh_token(data=payload)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def refresh_access_token_service(refresh_token: str, db: Session) -> Token:
    payload = decode_token(refresh_token)  # dict
    username = payload.get("sub")
    user_id = payload.get("user_id")
    if not username or not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = get_user_by_username_db(db, username)
    if not user: raise HTTPException(status_code=404, detail="User not found")
    if user.disabled: raise HTTPException(status_code=400, detail="User is deactivated")

    new_payload = {"sub": username, "user_id": str(user.id)}
    return {
        "access_token": create_access_token(new_payload),
        "refresh_token": create_refresh_token(new_payload),
        "token_type": "bearer",
    }
