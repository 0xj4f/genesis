from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from app.database.user_db_interface import get_user_by_username_db
from app.models.user_api_model import User, Token, TokenData, UserMinimal

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
    token experiration is working
    """
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(decoded)
        return decoded
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

    username: str = decode_token(token=token).get("sub")
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


def oauth_authenticate_internal_service(token: str = Depends(oauth2_scheme)) -> UserMinimal:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token=token)  # Assumes decode_token decodes the token and extracts the payload
    print(payload)
    user_id = payload.get("user_id")
    username = payload.get("sub")

    if not user_id or not username:
        raise credentials_exception

    return UserMinimal(user_id=user_id, username=username)

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