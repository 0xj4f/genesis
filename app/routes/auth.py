from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.auth_service import authenticate_user, create_access_token, get_token_service
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user_api_model import (
    Token
)

router = APIRouter()

@router.post("/token", tags=["auth"], response_model=Token)
def get_token_endpoint(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return get_token_service(
        db=db,
        form_data=form_data,
    )

# =============================================================================
# AUTHENTICATED - ROUTES
# =============================================================================
# def get_current_user(
#     token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
# ) -> User:
#     print(f"token: {token}")
#     credentials_exception = HTTPException(
#         status_code=401,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )

#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         print(f"username: {username}")
#         if username is None:
#             raise credentials_exception
#         # Verify user from the database here if necessary
#         token_data = TokenData(username=username)
#     except JWTError:
#         raise credentials_exception

#     user = get_user_by_username(db=db, username=token_data.username)
#     if user is None:
#         raise credentials_exception
#     if user.disabled:
#         raise HTTPException(status_code=400, detail="User is deactivated")
#     return user


# @app.get("/users/me/", response_model=User)
# def read_users_me(current_user: dict = Depends(get_current_user)):
#     return current_user

