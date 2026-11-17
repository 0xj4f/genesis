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
from app.models.user_api_model import UserCreate, UserUpdate, PasswordChangeRequest, validate_password_for_policy
from app.services.membership_service import password_policy_for
from sqlalchemy.orm import Session
from app.auth.auth import require_reauth
from app.config import get_settings
from app.services.verification_service import send_verification_email
from app.utils.security import hash_password
from app.services.membership_service import enroll_new_user
from fastapi import HTTPException

settings = get_settings()


def validate_existing_user(db: Session, email: str = None, username: str = None, exclude_user_id: str = None):
    email_user = get_user_by_email_db(db, email) if email else None
    username_user = get_user_by_username_db(db, username) if username else None
    if email_user and str(email_user.id) != exclude_user_id:
        raise HTTPException(status_code=400, detail="Email already registered")
    if username_user and str(username_user.id) != exclude_user_id:
        raise HTTPException(status_code=400, detail="Username already taken")


def create_user_service(db: Session, user_create: UserCreate, service_id: str | None = None,
                        ip: str | None = None, user_agent: str | None = None):
    """Sign-up. The account is active on the service it signed up on and pending on the others;
    where it came from is stored with it."""
    validate_existing_user(db, email=user_create.email, username=user_create.username)
    user_create.password = hash_password(user_create.password.get_secret_value())
    user = create_user_db(
        db, user_create,
        before_commit=lambda new_user: enroll_new_user(db, new_user, service_id),
        registered_via=service_id, registration_ip=ip, registration_user_agent=(user_agent or "")[:255] or None,
    )
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
    """Self-service password change: re-authenticate, store, sign out other sessions.

    The new password must meet the policy of the service this session signed in to.
    """
    validate_password_for_policy(request.new_password.get_secret_value(), password_policy_for(session.service_id))
    require_reauth(db, user, session, request.current_password)
    if request.current_password and (
        request.current_password.get_secret_value() == request.new_password.get_secret_value()
    ):
        # Otherwise a temporary password could simply be kept as the permanent one.
        raise ValueError("Choose a password different from your current one")
    password_hash = hash_password(request.new_password.get_secret_value())
    return set_user_password_db(db, user, password_hash, reason="password_changed", keep_session_id=session.id)


def delete_user_service(db: Session, user_id: str):
    return delete_user_by_id_db(db, user_id)


def get_user_by_email_service(db: Session, email: str):
    return get_user_by_email_db(db, email)


def get_user_by_username_service(db: Session, username: str):
    return get_user_by_username_db(db, username)
