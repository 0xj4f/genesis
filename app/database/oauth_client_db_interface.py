from sqlalchemy.orm import Session
from app.models.oauth_client_db_model import OAuthClient


def create_oauth_client_db(db: Session, data: dict) -> OAuthClient:
    client = OAuthClient(**data)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_oauth_client_by_id_db(db: Session, client_id: str) -> OAuthClient | None:
    return db.query(OAuthClient).filter(
        OAuthClient.id == client_id,
        OAuthClient.is_active == True,  # noqa: E712
    ).first()


def get_oauth_client_by_name_db(db: Session, client_name: str) -> OAuthClient | None:
    return db.query(OAuthClient).filter(OAuthClient.client_name == client_name).first()


def get_all_oauth_clients_db(db: Session) -> list[OAuthClient]:
    return db.query(OAuthClient).all()


def update_oauth_client_db(db: Session, client_id: str, update_data: dict) -> OAuthClient | None:
    client = db.query(OAuthClient).filter(OAuthClient.id == client_id).first()
    if not client:
        return None
    for key, value in update_data.items():
        if value is not None:
            setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client
