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