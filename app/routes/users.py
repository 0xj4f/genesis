from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.session import get_db
from app.services.user_service import (
    create_user_service,
    get_all_users_service,
    get_user_by_id_service,
    update_user_service,
    change_password_service,
    delete_user_service,
    get_user_by_username_service,
    get_user_by_email_service
)
from app.models.user_api_model import (
    UserCreate, User, UserUpdate, UserDeleteResponse, UserSearchRequest, PasswordChangeRequest,
)
from app.auth.auth import oauth_authenticate_current_user, current_user_with_claims, require_admin, require_reauth
from app.auth.policy import deny, ensure_can_manage
from app.utils.audit import security_event

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


@router.post("/me/password")
def change_own_password(
    body: PasswordChangeRequest,
    db: Session = Depends(get_db),
    auth=Depends(current_user_with_claims),
):
    """Change your password. Requires the current password (or, for SSO-only
    accounts, a recent sign-in). Other sessions are signed out."""
    current_user, _claims, session = auth
    try:
        change_password_service(db, current_user, session, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    security_event("password_changed", user_id=str(current_user.id))
    return {"message": "Password updated. Other sessions were signed out."}


@router.get("/{user_id}", response_model=User)
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(oauth_authenticate_current_user)):
    _require_self_or_staff(current_user, str(user_id), "read_user")
    user = get_user_by_id_service(db, str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=User)
def update_user(user_id: UUID, user_update: UserUpdate, db: Session = Depends(get_db), auth=Depends(current_user_with_claims)):
    current_user, _claims, session = auth
    _require_self_or_staff(current_user, str(user_id), "update_user")
    target = get_user_by_id_service(db, str(user_id), for_update=True)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_can_manage(current_user, target, "update_user")
    if user_update.password is not None:
        raise HTTPException(
            status_code=400,
            detail="Passwords cannot be changed here. Use POST /users/me/password "
            "(or POST /admin/users/{id}/password for administrators).",
        )
    is_self = str(current_user.id) == str(user_id)
    if is_self and user_update.email and user_update.email != target.email:
        require_reauth(db, current_user, session, user_update.current_password)
    try:
        user, pending = update_user_service(db, target, user_update, is_self)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return User.model_validate(user).model_copy(update={"email_change_pending": pending})

@router.delete("/{user_id}", response_model=UserDeleteResponse)
def delete_user(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(oauth_authenticate_current_user)):
    _require_self_or_staff(current_user, str(user_id), "delete_user")
    target = get_user_by_id_service(db, str(user_id), for_update=True)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "root":
        raise HTTPException(status_code=403, detail="Cannot delete ROOT user")
    ensure_can_manage(current_user, target, "delete_user")
    delete_user_service(db, str(user_id))
    return {"message": f"User with ID {user_id} has been successfully deleted"}

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


def _require_self_or_staff(current_user, user_id: str, action: str):
    # Checked before any lookup so other users' ids cannot be probed.
    if str(current_user.id) != user_id and current_user.role not in ("admin", "root"):
        deny(current_user, action, user_id)

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

@router.get("/me/", response_model=User)
def read_users_me(current_user: dict = Depends(oauth_authenticate_current_user)):
    return current_user
