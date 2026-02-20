from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.auth import get_current_root_admin, get_current_user, write_audit_log
from app.database.session import get_db
from app.models.user_api_model import AdminUserListItem, AdminUserUpdateRequest, UserMeResponse, UserMeUpdateRequest
from app.models.user_db_model import AuthProvider, User, UserIdentity, UserRole, UserStatus

user_router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@user_router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@user_router.put("/me", response_model=UserMeResponse)
def update_me(payload: UserMeUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    identity = (
        db.query(UserIdentity)
        .filter(UserIdentity.user_id == current_user.id, UserIdentity.provider == AuthProvider.native)
        .first()
    )
    if not identity:
        raise HTTPException(status_code=400, detail="Native identity not found")

    if payload.username:
        exists = (
            db.query(UserIdentity)
            .filter(
                UserIdentity.provider == AuthProvider.native,
                UserIdentity.username == payload.username,
                UserIdentity.user_id != current_user.id,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Username already taken")
        identity.username = payload.username

    if payload.email:
        exists = (
            db.query(UserIdentity)
            .filter(
                UserIdentity.provider == AuthProvider.native,
                UserIdentity.email == payload.email,
                UserIdentity.user_id != current_user.id,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Email already used")
        identity.email = payload.email

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    write_audit_log(db, actor_user_id=current_user.id, action="update_me", target_type="user", target_id=current_user.id)
    return current_user


@admin_router.get("/users", response_model=list[AdminUserListItem])
def list_users(_: User = Depends(get_current_root_admin), db: Session = Depends(get_db)):
    return db.query(User).all()


@admin_router.get("/users/{user_id}", response_model=AdminUserListItem)
def get_user(user_id: str, _: User = Depends(get_current_root_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@admin_router.patch("/users/{user_id}", response_model=AdminUserListItem)
def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    root_admin: User = Depends(get_current_root_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None:
        user.role = payload.role

    if payload.status is not None:
        user.status = payload.status
        user.disabled_at = datetime.utcnow() if payload.status == UserStatus.disabled else None

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        actor_user_id=root_admin.id,
        action="admin_update_user",
        target_type="user",
        target_id=user.id,
        metadata={"role": user.role.value, "status": user.status.value},
    )
    return user
