from sqlalchemy.orm import Session
from app.models.jwk_db_model import JWKKey
from datetime import datetime


def create_jwk_key_db(db: Session, data: dict) -> JWKKey:
    key = JWKKey(**data)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


def get_current_signing_key_db(db: Session) -> JWKKey | None:
    return db.query(JWKKey).filter(
        JWKKey.is_current == True,  # noqa: E712
        JWKKey.is_active == True,  # noqa: E712
    ).first()


def get_all_active_keys_db(db: Session) -> list[JWKKey]:
    return db.query(JWKKey).filter(JWKKey.is_active == True).all()  # noqa: E712


def rotate_key_db(db: Session, old_kid: str, new_kid: str) -> bool:
    old_key = db.query(JWKKey).filter(JWKKey.kid == old_kid).first()
    new_key = db.query(JWKKey).filter(JWKKey.kid == new_kid).first()
    if not old_key or not new_key:
        return False
    old_key.is_current = False
    old_key.rotated_at = datetime.utcnow()
    new_key.is_current = True
    db.commit()
    return True


def deactivate_key_db(db: Session, kid: str) -> bool:
    key = db.query(JWKKey).filter(JWKKey.kid == kid).first()
    if not key:
        return False
    key.is_active = False
    key.expires_at = datetime.utcnow()
    db.commit()
    return True
