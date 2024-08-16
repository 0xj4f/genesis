# auth.py
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import bcrypt
# import jwt
import os
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from app.database.user_db_interface import get_user_by_username_db
from app.models.user_api_model import User, Token, TokenData
from app.database.session import get_db

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

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Default to 15 minutes if not specified
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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

def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    print(f"token: {token}")
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        print(f"username: {username}")
        if username is None:
            raise credentials_exception
        # Verify user from the database here if necessary
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user_by_username_db(db=db, username=token_data.username)
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