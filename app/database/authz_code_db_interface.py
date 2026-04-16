from sqlalchemy.orm import Session
from app.models.authz_code_db_model import AuthorizationCode
from datetime import datetime


def create_authz_code_db(db: Session, data: dict) -> AuthorizationCode:
    code = AuthorizationCode(**data)
    db.add(code)
    db.commit()
    db.refresh(code)
    return code


def get_authz_code_db(db: Session, code: str) -> AuthorizationCode | None:
    return db.query(AuthorizationCode).filter(
        AuthorizationCode.code == code,
        AuthorizationCode.used == False,  # noqa: E712
        AuthorizationCode.expires_at > datetime.utcnow(),
    ).first()


def mark_authz_code_used_db(db: Session, code: str) -> bool:
    authz_code = db.query(AuthorizationCode).filter(AuthorizationCode.code == code).first()
    if not authz_code:
        return False
    authz_code.used = True
    db.commit()
    return True
