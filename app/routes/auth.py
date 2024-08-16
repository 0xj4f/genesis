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



