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

from app.auth.auth import oauth_authenticate_current_user, get_current_user
# @router.get("/users/me", response_model=User)
@router.get("/me/",tags=["users"], response_model=User)
def read_users_me(current_user: dict = Depends(oauth_authenticate_current_user)):
# def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user