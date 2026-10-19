from app.database.user_db_interface import (
    create_user_db,
    get_all_users_db,
    get_user_by_id_db,
    update_user_by_id_db,
    delete_user_by_id_db,
    get_user_by_email_db,
    get_user_by_username_db,
    set_user_password_db,
)
from app.models.user_api_model import UserCreate, UserUpdate, PasswordChangeRequest
from sqlalchemy.orm import Session
from app.auth.auth import require_reauth
from app.config import get_settings
from app.services.verification_service import send_verification_email
from app.utils.security import hash_password
from fastapi import HTTPException

settings = get_settings()


def validate_existing_user(db: Session, email: str = None, username: str = None, exclude_user_id: str = None):
    email_user = get_user_by_email_db(db, email) if email else None
    username_user = get_user_by_username_db(db, username) if username else None
    if email_user and str(email_user.id) != exclude_user_id:
        raise HTTPException(status_code=400, detail="Email already registered")
    if username_user and str(username_user.id) != exclude_user_id:
        raise HTTPException(status_code=400, detail="Username already taken")


def create_user_service(db: Session, user_create: UserCreate):
    validate_existing_user(db, email=user_create.email, username=user_create.username)
    user_create.password = hash_password(user_create.password.get_secret_value())
    user = create_user_db(db, user_create)
    # No-op unless EMAIL_VERIFY is enabled.
    send_verification_email(db, user)
    return user


def get_all_users_service(db: Session):
    return get_all_users_db(db)


def get_user_by_id_service(db: Session, user_id: str, for_update: bool = False):
    return get_user_by_id_db(db, user_id, for_update=for_update)


def update_user_service(db: Session, target, user_update: UserUpdate, is_self: bool):
    """Apply username/email changes. Returns (user, email_change_pending)."""
    validate_existing_user(db, email=user_update.email, username=user_update.username, exclude_user_id=str(target.id))
    new_email = user_update.email if user_update.email and user_update.email != target.email else None
    pending = bool(new_email and settings.EMAIL_VERIFY and is_self)
    if pending:
        # Keep the current address until the new one is proven.
        user_update = user_update.model_copy(update={"email": None})
    user = update_user_by_id_db(db, str(target.id), user_update)
    if pending:
        send_verification_email(db, user, email=new_email, purpose="change")
    elif new_email:
        # Changed by an administrator: applied now, but unverified until confirmed.
        send_verification_email(db, user)
    return user, pending


def change_password_service(db: Session, user, session, request: PasswordChangeRequest):
    """Self-service password change: re-authenticate, store, sign out other sessions."""
    require_reauth(db, user, session, request.current_password)
    password_hash = hash_password(request.new_password.get_secret_value())
    return set_user_password_db(db, user, password_hash, reason="password_changed", keep_session_id=session.id)


def delete_user_service(db: Session, user_id: str):
    return delete_user_by_id_db(db, user_id)


def get_user_by_email_service(db: Session, email: str):
    return get_user_by_email_db(db, email)


def get_user_by_username_service(db: Session, username: str):
    return get_user_by_username_db(db, username)
