from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
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
from app.auth.auth import oauth_authenticate_current_user, require_admin

router = APIRouter()

@router.post("/", response_model=User)
def create_user(user_create: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user_service(db, user_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[User])
def get_users(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return get_all_users_service(db)

@router.get("/{user_id}", response_model=User)
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(oauth_authenticate_current_user)):
    _check_owner_or_admin(current_user, str(user_id))
    user = get_user_by_id_service(db, str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=User)
def update_user(user_id: UUID, user_update: UserUpdate, db: Session = Depends(get_db), current_user=Depends(oauth_authenticate_current_user)):
    _check_owner_or_admin(current_user, str(user_id))
    target = get_user_by_id_service(db, str(user_id), for_update=True)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "root" and str(current_user.id) != str(user_id):
        raise HTTPException(status_code=403, detail="Cannot modify ROOT user")
    try:
        return update_user_service(db, str(user_id), user_update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}", response_model=UserDeleteResponse)
def delete_user(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(oauth_authenticate_current_user)):
    _check_owner_or_admin(current_user, str(user_id))
    target = get_user_by_id_service(db, str(user_id), for_update=True)
    if target and target.role == "root":
        raise HTTPException(status_code=403, detail="Cannot delete ROOT user")
    if delete_user_service(db, str(user_id)):
        return {"message": f"User with ID {user_id} has been successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.post("/search", response_model=User)
def search_user(request: UserSearchRequest, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    user = None
    if request.email:
        user = get_user_by_email_service(db, request.email)
    elif request.username:
        user = get_user_by_username_service(db, request.username)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")


def _check_owner_or_admin(current_user, user_id: str):
    if str(current_user.id) != user_id and current_user.role not in ("admin", "root"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

# ===========================================================================
# AUTHENTICATED ROUTES 
# ===========================================================================
"""
important notes in authenticated routes.
make sure that defined endpoints ends with "/"
example:
/user/me -> /users/me/
otherwise authentication process gets errors 
"""
from app.auth.auth import oauth_authenticate_current_user

@router.get("/me/", response_model=User)
def read_users_me(current_user: dict = Depends(oauth_authenticate_current_user)):
# def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
