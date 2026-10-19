from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models.oauth_account_db_model import OAuthAccount


def create_oauth_account_db(db: Session, data: dict) -> OAuthAccount:
    account = OAuthAccount(**data)
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="SSO account is already linked or registered")
    db.refresh(account)
    return account


def get_oauth_account_by_provider_db(db: Session, provider: str, provider_user_id: str) -> OAuthAccount | None:
    return db.query(OAuthAccount).filter(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    ).first()


def get_oauth_accounts_by_user_db(db: Session, user_id: str) -> list[OAuthAccount]:
    return db.query(OAuthAccount).filter(OAuthAccount.user_id == user_id).all()


def get_oauth_account_by_user_and_provider_db(db: Session, user_id: str, provider: str) -> OAuthAccount | None:
    return db.query(OAuthAccount).filter(
        OAuthAccount.user_id == user_id,
        OAuthAccount.provider == provider,
    ).first()


def delete_oauth_account_db(db: Session, account_id: str) -> bool:
    account = db.query(OAuthAccount).filter(OAuthAccount.id == account_id).first()
    if not account:
        return False
    db.delete(account)
    db.commit()
    return True
