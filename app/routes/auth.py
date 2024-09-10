from fastapi import APIRouter, Depends, HTTPException, status,Form
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.auth_service import get_token_service, refresh_access_token_service
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from app.models.user_api_model import (
    Token,
    UserMinimal
)
from app.auth.auth import oauth_authenticate_internal_service

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/token", tags=["auth"], response_model=Token)
def get_token_endpoint(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return get_token_service(
        db=db,
        form_data=form_data,
    )

# this should only be used in internal API call
@router.post("/token/validate", tags=["auth"], response_model=UserMinimal)
def validate_token(user: UserMinimal = Depends(oauth_authenticate_internal_service)):
    return user

@router.post("/refresh_token", tags=["auth"], response_model=Token)
def refresh_token_endpoint(refresh_token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return refresh_access_token_service(refresh_token=refresh_token, db=db)