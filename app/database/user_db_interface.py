from app.models.user_db_model import User
from app.models.user_api_model import UserCreate, UserUpdate
from sqlalchemy.orm import Session


def create_user_db(db: Session, user_create: UserCreate) -> User:
    data = user_create.model_dump()
    # password is already hashed by the service layer (plain string at this point)
    db_user = User(**data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_users_db(db: Session):
    return db.query(User).all()


def get_user_by_id_db(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()


def update_user_by_id_db(db: Session, user_id: str, user_update: UserUpdate):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user_by_id_db(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    # Clean up non-cascaded FKs
    from app.models.authz_code_db_model import AuthorizationCode
    db.query(AuthorizationCode).filter(AuthorizationCode.user_id == user_id).delete()
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
