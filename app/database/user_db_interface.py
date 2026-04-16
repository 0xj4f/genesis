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
