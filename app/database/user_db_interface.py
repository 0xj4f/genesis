from app.models.user_db_model import User
from app.models.user_api_model import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from datetime import datetime


def create_user_db(db: Session, user_create: UserCreate) -> User:
    data = user_create.model_dump()
    # password is already hashed by the service layer (plain string at this point)
    db_user = User(**data)
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered or username already taken")
    db.refresh(db_user)
    return db_user


def get_all_users_db(db: Session):
    return db.query(User).all()


def get_user_by_id_db(db: Session, user_id: str, for_update: bool = False):
    query = db.query(User).filter(User.id == user_id)
    if for_update:
        query = query.with_for_update().populate_existing()
    return query.first()


def update_user_by_id_db(db: Session, user_id: str, user_update: UserUpdate):
    """Apply username/email changes. Passwords are changed with set_user_password_db."""
    user = get_user_by_id_db(db, user_id, for_update=True)
    if not user:
        return None
    update_data = user_update.model_dump(exclude_unset=True, include={"username", "email"})
    if update_data.get("email") and update_data["email"] != user.email:
        # Verification belongs to the verified address, not arbitrary replacements.
        user.email_verified = False
        user.email_verified_at = None
    for key, value in update_data.items():
        if value is not None:
            setattr(user, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered or username already taken")
    db.refresh(user)
    return user


def set_user_password_db(db: Session, user: User, password_hash: str, reason: str, keep_session_id: str = None) -> User:
    """Store a new password hash and revoke the user's other sessions."""
    from app.models.session_db_model import Session as LoginSession
    user.password = password_hash
    sessions = db.query(LoginSession).filter(
        LoginSession.user_id == str(user.id), LoginSession.is_active == True,  # noqa: E712
    )
    if keep_session_id:
        sessions = sessions.filter(LoginSession.id != keep_session_id)
    sessions.update({"is_active": False, "revoked_at": datetime.utcnow(), "revoked_reason": reason}, synchronize_session=False)
    db.commit()
    db.refresh(user)
    return user


def delete_user_by_id_db(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    # Clean up non-cascaded FKs
    from app.models.authz_code_db_model import AuthorizationCode
    from app.models.email_verification_db_model import EmailVerificationToken
    from app.models.profile_db_model import Profile
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user_id).delete()
    db.query(AuthorizationCode).filter(AuthorizationCode.user_id == user_id).delete()
    db.query(Profile).filter(Profile.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return user


def get_user_by_email_db(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username_db(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_provider_db(db: Session, provider: str, provider_id: str):
    return db.query(User).filter(
        User.auth_provider == provider,
        User.auth_provider_id == provider_id,
    ).first()


def get_users_paginated_db(db: Session, page: int = 1, per_page: int = 20, search: str = None):
    query = db.query(User)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (User.username.ilike(like)) | (User.email.ilike(like))
        )
    query = query.order_by(User.created_at.desc())
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    return users, total


def get_user_analytics_db(db: Session) -> dict:
    from sqlalchemy import func as sqlfunc
    from datetime import datetime, timedelta

    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()  # noqa: E712
    native = db.query(User).filter(User.is_native == True).count()  # noqa: E712
    sso = total - native
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_week = db.query(User).filter(User.created_at >= week_ago).count()
    admins = db.query(User).filter(User.role.in_(["admin", "root"])).count()

    # Provider breakdown
    rows = db.query(User.auth_provider, sqlfunc.count(User.id)).group_by(User.auth_provider).all()
    breakdown = {row[0]: row[1] for row in rows}

    return {
        "total_users": total,
        "active_users": active,
        "native_count": native,
        "sso_count": sso,
        "new_this_week": new_week,
        "admin_count": admins,
        "provider_breakdown": breakdown,
    }
