from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
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
    validate_password_for_policy,
)
from app.auth.auth import (
    oauth_authenticate_current_user, oauth_authenticate_pending_user, current_user_with_claims,
    current_user_with_claims_pending, require_genesis_admin, require_reauth,
)
from app.services.membership_service import password_policy_for, resolve_service, scope_service, scoped_role
from app.auth.policy import deny, ensure_can_manage
from app.utils.audit import security_event

router = APIRouter()

def check_password_policy(password: str, service_id: str | None, field: str) -> None:
    """The service's password policy, reported in the same 422 shape as model validation."""
    try:
        validate_password_for_policy(password, password_policy_for(service_id))
    except ValueError as e:
        raise RequestValidationError([{
            "type": "value_error", "loc": ("body", field), "msg": f"Value error, {e}", "input": None,
        }])


@router.post("/", response_model=User)
def create_user(user_create: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Sign up. The calling service (its Origin, or client_id) sets the password policy;
    the account is active there and pending on the other services."""
    service_id = resolve_service(request, user_create.client_id)
    check_password_policy(user_create.password.get_secret_value(), service_id, "password")
    try:
        user = create_user_service(
            db, user_create, service_id,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        security_event("user_registered", target=str(user.id), service=service_id)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[User])
def get_users(db: Session = Depends(get_db), current_user=Depends(require_genesis_admin)):
    return get_all_users_service(db)


@router.post("/me/password")
def change_own_password(
    body: PasswordChangeRequest,
    db: Session = Depends(get_db),
    auth=Depends(current_user_with_claims_pending),
):
    """Change your password. Requires the current password (or, for SSO-only
    accounts, a recent sign-in). Other sessions are signed out."""
    current_user, _claims, session = auth
    check_password_policy(body.new_password.get_secret_value(), session.service_id, "new_password")
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
    security_event("user_updated", actor=str(current_user.id), target=str(user.id))
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
    security_event("user_deleted", actor=str(current_user.id), target=str(user_id))
    return {"message": f"User with ID {user_id} has been successfully deleted"}

@router.post("/search", response_model=User)
def search_user(request: UserSearchRequest, db: Session = Depends(get_db), current_user=Depends(require_genesis_admin)):
    user = None
    if request.email:
        user = get_user_by_email_service(db, request.email)
    elif request.username:
        user = get_user_by_username_service(db, request.username)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")


def _require_self_or_staff(current_user, user_id: str, action: str):
    # Checked before any lookup so other users' ids cannot be probed. Other accounts are
    # shared by every service, so a service's admin manages them only through /admin/users.
    role = scoped_role(current_user)
    if str(current_user.id) == user_id or role == "root" or (role == "admin" and not scope_service(current_user)):
        return
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
def read_users_me(current_user: dict = Depends(oauth_authenticate_pending_user)):
    """Your account as the token's service sees it: the role there, and which service it is."""
    membership = getattr(current_user, "scope_membership", None)
    return User.model_validate(current_user).model_copy(update={
        "role": scoped_role(current_user),
        "service": scope_service(current_user),
        "membership_status": membership.status if membership else None,
    })
